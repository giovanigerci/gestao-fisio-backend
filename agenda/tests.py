from datetime import date, time, timedelta
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from profissionais.models import Profissional
from clinicas.models import Clinica
from pacientes.models import Paciente
from agenda.models import Agendamento

class ConfirmarDiaAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dr_silva', password='password123')
        self.profissional = Profissional.objects.create(
            usuario=self.user,
            telefone='11999999999',
            especialidade='Fisioterapia Geral',
            crefito='12345-F'
        )

        self.user2 = User.objects.create_user(username='dr_santos', password='password123')
        self.profissional2 = Profissional.objects.create(
            usuario=self.user2,
            telefone='11888888888',
            especialidade='Pilates',
            crefito='67890-F'
        )

        self.clinica = Clinica.objects.create(
            profissional=self.profissional,
            nome='Clínica Reabilitar',
            endereco='Rua A, 100',
            valor_por_atendimento=150.00
        )

        self.paciente1 = Paciente.objects.create(
            profissional=self.profissional,
            nome='João Silva',
            cpf='111.111.111-11',
            telefone='11911111111'
        )
        self.paciente2 = Paciente.objects.create(
            profissional=self.profissional,
            nome='Maria Souza',
            cpf='222.222.222-22',
            telefone='11922222222'
        )
        self.paciente3 = Paciente.objects.create(
            profissional=self.profissional,
            nome='Carlos Lima',
            cpf='333.333.333-33',
            telefone='11933333333'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sem_parametro_data(self):
        res = self.client.patch('/api/agendamentos/confirmar-dia/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('erro', res.data)

    def test_data_invalida(self):
        res = self.client.patch('/api/agendamentos/confirmar-dia/?data=data-invalida')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_data_futura_rejeitada(self):
        amanha = timezone.localdate() + timedelta(days=1)
        res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={amanha.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('futura', res.data['erro'])

    def test_hoje_antes_do_fim_do_expediente_rejeitado(self):
        hoje = timezone.localdate()
        # Cria agendamento com hora_fim no futuro do dia de hoje
        Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente1,
            data=hoje,
            hora_inicio=time(14, 0),
            hora_fim=time(23, 59),
            status=Agendamento.Status.AGENDADO
        )

        # Mock timezone.localtime().time() para 15:00 (antes das 23:59)
        with patch('django.utils.timezone.localtime') as mock_localtime:
            agora_mock = timezone.now().replace(hour=15, minute=0, second=0)
            mock_localtime.return_value = agora_mock
            res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={hoje.strftime("%Y-%m-%d")}')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('expediente', res.data['erro'])

    def test_sem_agendamentos_no_dia(self):
        ontem = timezone.localdate() - timedelta(days=1)
        res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={ontem.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Não há agendamentos cadastrados', res.data['erro'])

    def test_sem_agendamentos_pendentes(self):
        ontem = timezone.localdate() - timedelta(days=1)
        # Cria agendamentos apenas Realizados ou Cancelados
        Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente1,
            data=ontem,
            hora_inicio=time(9, 0),
            hora_fim=time(10, 0),
            status=Agendamento.Status.REALIZADO
        )
        Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente2,
            data=ontem,
            hora_inicio=time(11, 0),
            hora_fim=time(12, 0),
            status=Agendamento.Status.CANCELADO
        )

        res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={ontem.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Não há agendamentos pendentes', res.data['erro'])

    def test_sucesso_confirmacao_em_lote_e_preservacao_cancelados(self):
        ontem = timezone.localdate() - timedelta(days=1)
        ag1 = Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente1,
            data=ontem,
            hora_inicio=time(9, 0),
            hora_fim=time(10, 0),
            status=Agendamento.Status.AGENDADO
        )
        ag2 = Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente2,
            data=ontem,
            hora_inicio=time(10, 30),
            hora_fim=time(11, 30),
            status=Agendamento.Status.AGENDADO
        )
        ag_canc = Agendamento.objects.create(
            profissional=self.profissional,
            clinica=self.clinica,
            paciente=self.paciente3,
            data=ontem,
            hora_inicio=time(14, 0),
            hora_fim=time(15, 0),
            status=Agendamento.Status.CANCELADO
        )

        res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={ontem.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_confirmados'], 2)

        ag1.refresh_from_db()
        ag2.refresh_from_db()
        ag_canc.refresh_from_db()

        self.assertEqual(ag1.status, Agendamento.Status.REALIZADO)
        self.assertEqual(ag2.status, Agendamento.Status.REALIZADO)
        self.assertEqual(ag_canc.status, Agendamento.Status.CANCELADO)

    def test_isolamento_de_profissional(self):
        ontem = timezone.localdate() - timedelta(days=1)
        clinica2 = Clinica.objects.create(
            profissional=self.profissional2,
            nome='Clínica Pilates',
            endereco='Rua B, 200',
            valor_por_atendimento=100.00
        )
        paciente_outro = Paciente.objects.create(
            profissional=self.profissional2,
            nome='Outro Paciente',
            cpf='999.999.999-99',
            telefone='11988888888'
        )
        ag_outro = Agendamento.objects.create(
            profissional=self.profissional2,
            clinica=clinica2,
            paciente=paciente_outro,
            data=ontem,
            hora_inicio=time(14, 0),
            hora_fim=time(15, 0),
            status=Agendamento.Status.AGENDADO
        )

        # Usuário 1 tenta confirmar o dia (onde ele mesmo não tem agendamentos)
        res = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={ontem.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Agendamento do profissional 2 continua intacto como AGENDADO
        ag_outro.refresh_from_db()
        self.assertEqual(ag_outro.status, Agendamento.Status.AGENDADO)

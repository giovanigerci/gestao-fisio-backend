from datetime import date, datetime, time, timedelta
from decimal import Decimal
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

        # Relógio às 15:00 de hoje no fuso do projeto (antes das 23:59).
        # Montado a partir da data local: timezone.now().replace(hour=15) usaria a data UTC,
        # que entre 21h e 0h (UTC-3) já é o dia seguinte — e o teste falhava nesse horário.
        with patch('django.utils.timezone.localtime') as mock_localtime:
            agora_mock = timezone.make_aware(datetime.combine(hoje, time(15, 0)))
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


class ValorCobradoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dr_valor', password='x')
        self.profissional = Profissional.objects.create(
            usuario=self.user, telefone='1', especialidade='x', crefito='VALOR-F'
        )
        self.clinica = Clinica.objects.create(
            profissional=self.profissional, nome='Clínica 40', endereco='Rua', valor_por_atendimento=Decimal('40.00')
        )
        self.outra_clinica = Clinica.objects.create(
            profissional=self.profissional, nome='Clínica 100', endereco='Rua', valor_por_atendimento=Decimal('100.00')
        )
        self.pacientes = [
            Paciente.objects.create(profissional=self.profissional, nome=f'P{i}', cpf=f'999.999.999-0{i}', telefone='1')
            for i in range(3)
        ]
        self.ontem = timezone.localdate() - timedelta(days=1)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def agendar(self, paciente=None, clinica=None, experimental=False, hora=9):
        return Agendamento.objects.create(
            profissional=self.profissional, clinica=clinica or self.clinica, paciente=paciente or self.pacientes[0],
            data=self.ontem, hora_inicio=time(hora, 0), hora_fim=time(hora + 1, 0), eh_experimental=experimental,
        )

    def patch(self, agendamento, **dados):
        response = self.client.patch(f'/api/agendamentos/{agendamento.id}/', dados)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agendamento.refresh_from_db()
        return response

    def reajustar(self, clinica, valor):
        clinica.valor_por_atendimento = Decimal(valor)
        clinica.save()

    def test_agendado_nao_tem_valor_congelado(self):
        agendamento = self.agendar()

        self.assertIsNone(agendamento.valor_cobrado)

    def test_confirmar_congela_o_valor_e_reajuste_nao_altera(self):
        agendamento = self.agendar()
        self.patch(agendamento, status='RE')
        self.reajustar(self.clinica, '60.00')

        response = self.client.get(f'/api/agendamentos/{agendamento.id}/')

        self.assertEqual(agendamento.valor_cobrado, Decimal('40.00'))
        self.assertEqual(response.data['valor_calculado'], Decimal('40.00'))

    def test_agendado_acompanha_o_valor_atual_da_clinica(self):
        agendamento = self.agendar()
        self.reajustar(self.clinica, '60.00')

        response = self.client.get(f'/api/agendamentos/{agendamento.id}/')

        self.assertEqual(response.data['valor_calculado'], Decimal('60.00'))

    def test_experimental_realizado_congela_zero(self):
        agendamento = self.agendar(experimental=True)

        self.patch(agendamento, status='RE')

        self.assertEqual(agendamento.valor_cobrado, Decimal('0.00'))

    def test_desfazer_a_confirmacao_limpa_o_valor(self):
        agendamento = self.agendar()
        self.patch(agendamento, status='RE')
        self.reajustar(self.clinica, '60.00')

        self.patch(agendamento, status='AG')
        self.assertIsNone(agendamento.valor_cobrado)

        self.patch(agendamento, status='RE')  # reconfirmado depois do reajuste: vale o preço novo
        self.assertEqual(agendamento.valor_cobrado, Decimal('60.00'))

    def test_corrigir_clinica_ou_experimental_de_realizado_recalcula(self):
        agendamento = self.agendar()
        self.patch(agendamento, status='RE')

        self.patch(agendamento, clinica=self.outra_clinica.id)
        self.assertEqual(agendamento.valor_cobrado, Decimal('100.00'))

        self.patch(agendamento, eh_experimental=True)
        self.assertEqual(agendamento.valor_cobrado, Decimal('0.00'))

    def test_editar_outro_campo_de_realizado_nao_recalcula(self):
        agendamento = self.agendar()
        self.patch(agendamento, status='RE')
        self.reajustar(self.clinica, '60.00')

        self.patch(agendamento, hora_inicio='10:00', hora_fim='11:00')

        self.assertEqual(agendamento.valor_cobrado, Decimal('40.00'))

    def test_confirmar_dia_congela_o_valor_de_cada_clinica_em_um_unico_update(self):
        normal = self.agendar(self.pacientes[0], self.clinica, hora=8)
        outra = self.agendar(self.pacientes[1], self.outra_clinica, hora=9)
        experimental = self.agendar(self.pacientes[2], self.clinica, experimental=True, hora=10)

        response = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={self.ontem}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        valores = {a.id: a.valor_cobrado for a in Agendamento.objects.filter(id__in=[normal.id, outra.id, experimental.id])}
        self.assertEqual(valores, {normal.id: Decimal('40.00'), outra.id: Decimal('100.00'), experimental.id: Decimal('0.00')})

    def test_migration_preenche_realizados_antigos_com_o_valor_atual(self):
        from importlib import import_module
        from django.apps import apps

        realizado = self.agendar(self.pacientes[0], self.outra_clinica, hora=8)
        experimental = self.agendar(self.pacientes[1], experimental=True, hora=9)
        agendado = self.agendar(self.pacientes[2], hora=10)
        # Simula dados anteriores ao campo: realizados sem valor congelado
        Agendamento.objects.filter(id__in=[realizado.id, experimental.id]).update(status='RE', valor_cobrado=None)

        migration = import_module('agenda.migrations.0006_agendamento_valor_cobrado')
        migration.congelar_valor_dos_realizados(apps, None)

        valores = dict(Agendamento.objects.values_list('id', 'valor_cobrado'))
        self.assertEqual(valores[realizado.id], Decimal('100.00'))
        self.assertEqual(valores[experimental.id], Decimal('0.00'))
        self.assertIsNone(valores[agendado.id])

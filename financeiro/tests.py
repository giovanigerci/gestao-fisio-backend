from datetime import date, datetime, time, timezone as dt_tz
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from agenda.models import Agendamento
from clinicas.models import Clinica
from pacientes.models import Paciente
from profissionais.models import Profissional

RE, AG, CA = Agendamento.Status.REALIZADO, Agendamento.Status.AGENDADO, Agendamento.Status.CANCELADO


class ReceitaTestCase(TestCase):
    """
    Regra central do projeto (README): receita do bloco = valor_por_atendimento × atendimentos
    realizados, sem contar sessões experimentais. Calculada na consulta, nunca persistida.
    """

    def setUp(self):
        user = User.objects.create_user(username='dr_silva', password='x')
        self.profissional = Profissional.objects.create(
            usuario=user, telefone='1', especialidade='Pilates', crefito='12345-F'
        )
        self.clinica_a = Clinica.objects.create(
            profissional=self.profissional, nome='A - Studio', endereco='Rua A', valor_por_atendimento=Decimal('40.00')
        )
        self.clinica_b = Clinica.objects.create(
            profissional=self.profissional, nome='B - Centro', endereco='Rua B', valor_por_atendimento=Decimal('100.00')
        )
        self.pacientes = [
            Paciente.objects.create(profissional=self.profissional, nome=f'Paciente {i}', cpf=f'000.000.000-0{i}', telefone='1')
            for i in range(4)
        ]
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def agendar(self, clinica, paciente, dia, status=RE, experimental=False, hora=14):
        return Agendamento.objects.create(
            profissional=self.profissional, clinica=clinica, paciente=paciente, data=dia,
            hora_inicio=time(hora, 0), hora_fim=time(hora + 1, 0), status=status, eh_experimental=experimental,
        )

    def resumo(self, periodo='mes', data='2026-03-15'):
        params = {'periodo': periodo}
        if data:
            params['data'] = data
        return self.client.get('/api/resumo-financeiro/', params).data

    def por_clinica(self, resumo):
        return {item['clinica__nome']: (item['total_atendimentos'], item['receita_total']) for item in resumo['por_clinica']}

    def test_exemplo_do_readme_bloco_com_sessao_experimental(self):
        # 14h, Clínica A (R$ 40), 3 pacientes no mesmo horário, um deles experimental → R$ 80
        dia = date(2026, 3, 10)
        self.agendar(self.clinica_a, self.pacientes[0], dia)
        self.agendar(self.clinica_a, self.pacientes[1], dia)
        self.agendar(self.clinica_a, self.pacientes[2], dia, experimental=True)

        resumo = self.resumo()

        self.assertEqual(self.por_clinica(resumo), {'A - Studio': (2, Decimal('80.00'))})
        self.assertEqual(resumo['total_geral'], Decimal('80.00'))

    def test_so_atendimentos_realizados_entram_na_receita(self):
        dia = date(2026, 3, 10)
        self.agendar(self.clinica_a, self.pacientes[0], dia, status=RE)
        self.agendar(self.clinica_a, self.pacientes[1], dia, status=AG)
        self.agendar(self.clinica_a, self.pacientes[2], dia, status=CA)

        self.assertEqual(self.resumo()['total_geral'], Decimal('40.00'))

    def test_agrupa_por_clinica_e_soma_o_total_geral(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 2))
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 9))
        self.agendar(self.clinica_b, self.pacientes[2], date(2026, 3, 20))

        resumo = self.resumo()

        self.assertEqual(self.por_clinica(resumo), {
            'A - Studio': (2, Decimal('80.00')),
            'B - Centro': (1, Decimal('100.00')),
        })
        self.assertEqual(resumo['total_geral'], Decimal('180.00'))
        self.assertEqual([c['clinica__nome'] for c in resumo['por_clinica']], ['A - Studio', 'B - Centro'])

    def test_periodo_mes_inclui_do_dia_1_ao_ultimo_dia(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 2, 28))  # mês anterior
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 1))
        self.agendar(self.clinica_a, self.pacientes[2], date(2026, 3, 31))
        self.agendar(self.clinica_a, self.pacientes[3], date(2026, 4, 1))  # mês seguinte

        self.assertEqual(self.resumo('mes', '2026-03-15')['total_geral'], Decimal('80.00'))

    def test_periodo_semana_vai_de_domingo_a_sabado(self):
        # Mesma semana da agenda. 18/03/2026 é quarta: semana de domingo 15/03 a sábado 21/03
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 14))  # sábado anterior
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 15))  # domingo
        self.agendar(self.clinica_a, self.pacientes[2], date(2026, 3, 21))  # sábado
        self.agendar(self.clinica_a, self.pacientes[3], date(2026, 3, 22))  # domingo seguinte

        self.assertEqual(self.resumo('semana', '2026-03-18')['total_geral'], Decimal('80.00'))

    def test_periodo_semana_a_partir_do_proprio_domingo_e_do_sabado(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 15))  # domingo
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 21))  # sábado

        for data in ('2026-03-15', '2026-03-21'):
            with self.subTest(data=data):
                self.assertEqual(self.resumo('semana', data)['total_geral'], Decimal('80.00'))

    def test_receita_e_calculada_na_hora_com_o_valor_atual_da_clinica(self):
        # Decisão documentada no README: a receita é derivada, então reajustar o valor da clínica
        # recalcula também os atendimentos já realizados
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 10))
        self.clinica_a.valor_por_atendimento = Decimal('55.00')
        self.clinica_a.save()

        self.assertEqual(self.resumo()['total_geral'], Decimal('55.00'))

    def test_sem_data_usa_o_dia_atual_no_fuso_do_brasil(self):
        # 31/01 às 22h30 em Brasília (01h30 UTC de 01/02): o "mês atual" ainda é janeiro
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 1, 31))
        noite = datetime(2026, 2, 1, 1, 30, tzinfo=dt_tz.utc)

        with patch('django.utils.timezone.now', return_value=noite):
            resumo = self.resumo('mes', data=None)

        self.assertEqual(resumo['total_geral'], Decimal('40.00'))

    def test_valor_calculado_do_agendamento(self):
        normal = self.agendar(self.clinica_b, self.pacientes[0], date(2026, 3, 10), status=AG)
        experimental = self.agendar(self.clinica_b, self.pacientes[1], date(2026, 3, 10), status=AG, experimental=True)

        valores = {
            a['id']: a['valor_calculado']
            for a in self.client.get('/api/agendamentos/', {'data_inicio': '2026-03-01', 'data_fim': '2026-03-31'}).data
        }

        self.assertEqual(valores[normal.id], Decimal('100.00'))
        self.assertEqual(valores[experimental.id], 0)

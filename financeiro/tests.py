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


class BaseFinanceiroTestCase(TestCase):
    """Cenário comum: um profissional com duas clínicas (R$ 40 e R$ 100) e quatro pacientes."""

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


class ReceitaTestCase(BaseFinanceiroTestCase):
    """
    Regra central do projeto (README): receita do bloco = soma do valor cobrado nos atendimentos
    realizados (congelado na confirmação), sem contar sessões experimentais.
    """

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

    def test_reajuste_da_clinica_nao_altera_atendimentos_ja_realizados(self):
        # O valor é congelado quando o atendimento é realizado: o reajuste só vale daí para frente
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 10))
        self.clinica_a.valor_por_atendimento = Decimal('55.00')
        self.clinica_a.save()
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 20))

        self.assertEqual(self.resumo()['total_geral'], Decimal('95.00'))  # 40 (antes) + 55 (depois)

    def test_data_invalida_responde_400(self):
        response = self.client.get('/api/resumo-financeiro/', {'data': '2026-13-45'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('data', response.data)

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


class EvolucaoReceitaTestCase(BaseFinanceiroTestCase):
    url = '/api/resumo-financeiro/evolucao/'

    def evolucao(self, periodo='mes', data='2026-03-15'):
        response = self.client.get(self.url, {'periodo': periodo, 'data': data})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_serie_diaria_do_mes_com_acumulado(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 2))
        self.agendar(self.clinica_b, self.pacientes[1], date(2026, 3, 2))
        self.agendar(self.clinica_a, self.pacientes[2], date(2026, 3, 10))

        dados = self.evolucao()
        dias = {d['data']: d for d in dados['dias']}

        self.assertEqual(len(dados['dias']), 31)
        self.assertEqual(dados['periodo'], {'inicio': date(2026, 3, 1), 'fim': date(2026, 3, 31)})
        self.assertEqual(dias[date(2026, 3, 2)]['realizado'], Decimal('140.00'))
        self.assertEqual(dias[date(2026, 3, 5)]['acumulado'], Decimal('140.00'))
        self.assertEqual(dias[date(2026, 3, 31)]['acumulado'], Decimal('180.00'))
        self.assertEqual(dados['totais']['realizado'], Decimal('180.00'))

    def test_previsto_soma_agendados_pelo_preco_atual_e_ignora_experimental_e_cancelado(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 2))  # realizado: 40
        self.agendar(self.clinica_b, self.pacientes[1], date(2026, 3, 20), status=AG)  # previsto: 100
        self.agendar(self.clinica_b, self.pacientes[2], date(2026, 3, 20), status=AG, experimental=True)  # 0
        self.agendar(self.clinica_b, self.pacientes[3], date(2026, 3, 21), status=CA)  # fora

        dados = self.evolucao()
        dias = {d['data']: d for d in dados['dias']}

        self.assertEqual(dias[date(2026, 3, 20)]['previsto'], Decimal('100.00'))
        self.assertEqual(dias[date(2026, 3, 31)]['acumulado'], Decimal('40.00'))
        self.assertEqual(dias[date(2026, 3, 31)]['acumulado_com_previsto'], Decimal('140.00'))
        self.assertEqual(dados['totais'], {
            'realizado': Decimal('40.00'), 'previsto': Decimal('100.00'), 'anterior': Decimal('0.00'),
        })

    def test_compara_com_o_mes_anterior(self):
        self.agendar(self.clinica_b, self.pacientes[0], date(2026, 2, 10))
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 10))

        anterior = self.evolucao()['anterior']

        self.assertEqual((anterior['inicio'], anterior['fim']), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(len(anterior['dias']), 28)
        self.assertEqual(anterior['dias'][-1]['acumulado'], Decimal('100.00'))

    def test_semana_de_domingo_a_sabado_comparada_com_a_semana_anterior(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 15))  # domingo
        self.agendar(self.clinica_b, self.pacientes[1], date(2026, 3, 14))  # sábado anterior

        dados = self.evolucao('semana', '2026-03-18')

        self.assertEqual([d['data'] for d in dados['dias']][0::6], [date(2026, 3, 15), date(2026, 3, 21)])
        self.assertEqual(dados['totais']['realizado'], Decimal('40.00'))
        self.assertEqual(dados['totais']['anterior'], Decimal('100.00'))

    def test_uma_unica_consulta_agregada(self):
        for i, dia in enumerate((2, 10, 20)):
            self.agendar(self.clinica_a, self.pacientes[i], date(2026, 3, dia))

        # Uma única consulta agregada cobre o período atual e o anterior (a autenticação real
        # acrescenta só a busca do usuário/profissional, que não cresce com o volume de dados)
        with self.assertNumQueries(1):
            self.client.get(self.url, {'data': '2026-03-15'})

    def test_parametros_invalidos_respondem_400(self):
        for params in ({'data': 'ontem'}, {'periodo': 'trimestre'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)


class HistoricoReceitaTestCase(BaseFinanceiroTestCase):
    url = '/api/resumo-financeiro/historico/'

    def historico(self, agrupar='mes', data='2026-03-15'):
        response = self.client.get(self.url, {'agrupar': agrupar, 'data': data})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_ultimos_12_meses_comparados_com_o_ano_anterior(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 10))  # mês de referência
        self.agendar(self.clinica_b, self.pacientes[1], date(2025, 4, 10))  # primeiro mês da janela
        self.agendar(self.clinica_b, self.pacientes[2], date(2025, 3, 10))  # mesmo mês do ano anterior
        self.agendar(self.clinica_b, self.pacientes[3], date(2024, 3, 10))  # fora de tudo

        dados = self.historico()
        periodos = {p['periodo']: p for p in dados['periodos']}

        self.assertEqual(len(dados['periodos']), 12)
        self.assertEqual((dados['periodos'][0]['periodo'], dados['periodos'][-1]['periodo']), ('2025-04', '2026-03'))
        self.assertEqual(periodos['2026-03']['receita'], Decimal('40.00'))
        self.assertEqual(periodos['2026-03']['receita_periodo_anterior'], Decimal('100.00'))
        self.assertEqual(periodos['2025-04']['receita'], Decimal('100.00'))
        self.assertEqual(periodos['2025-05']['receita'], Decimal('0.00'))

    def test_resumo_com_total_media_melhor_mes_e_variacao(self):
        self.agendar(self.clinica_b, self.pacientes[0], date(2026, 1, 10))
        self.agendar(self.clinica_b, self.pacientes[1], date(2026, 1, 11))
        self.agendar(self.clinica_a, self.pacientes[2], date(2026, 3, 10))
        self.agendar(self.clinica_b, self.pacientes[3], date(2025, 2, 10))  # janela anterior: 100

        resumo = self.historico()['resumo']

        self.assertEqual(resumo['total'], Decimal('240.00'))
        self.assertEqual(resumo['media'], Decimal('20.00'))
        self.assertEqual(resumo['melhor_periodo']['periodo'], '2026-01')
        self.assertEqual(resumo['total_periodo_anterior'], Decimal('100.00'))
        self.assertEqual(resumo['variacao_percentual'], Decimal('140.0'))

    def test_experimental_nao_conta_como_receita_nem_atendimento(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2026, 3, 10))
        self.agendar(self.clinica_a, self.pacientes[1], date(2026, 3, 10), experimental=True)

        marco = self.historico()['periodos'][-1]

        self.assertEqual((marco['receita'], marco['atendimentos']), (Decimal('40.00'), 1))

    def test_sem_atendimentos_nao_inventa_melhor_periodo_nem_variacao(self):
        resumo = self.historico()['resumo']

        self.assertEqual(resumo['total'], Decimal('0.00'))
        self.assertIsNone(resumo['melhor_periodo'])
        self.assertIsNone(resumo['variacao_percentual'])

    def test_agrupado_por_ano_desde_o_primeiro_atendimento(self):
        self.agendar(self.clinica_a, self.pacientes[0], date(2024, 5, 1))
        self.agendar(self.clinica_b, self.pacientes[1], date(2026, 2, 1))

        dados = self.historico('ano')

        self.assertEqual(
            [(p['periodo'], p['receita'], p['receita_periodo_anterior']) for p in dados['periodos']],
            [('2024', Decimal('40.00'), Decimal('0.00')),
             ('2025', Decimal('0.00'), Decimal('40.00')),
             ('2026', Decimal('100.00'), Decimal('0.00'))],
        )

    def test_uma_unica_consulta_agregada_mesmo_com_muitos_meses(self):
        for i, mes in enumerate((1, 6, 11)):
            self.agendar(self.clinica_a, self.pacientes[i], date(2025, mes, 10))

        with self.assertNumQueries(1):
            self.client.get(self.url, {'data': '2026-03-15'})  # 24 meses (12 + ano anterior) em uma consulta
        with self.assertNumQueries(1):
            self.client.get(self.url, {'agrupar': 'ano', 'data': '2026-03-15'})

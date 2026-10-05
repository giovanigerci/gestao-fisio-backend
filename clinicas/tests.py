from datetime import date, time
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from agenda.models import Agendamento
from clinicas.models import Clinica
from pacientes.models import Paciente
from rest_framework import status
from rest_framework.test import APIClient
from profissionais.models import Profissional


class ValorPorAtendimentoAPITestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='dr_silva', password='password123')
        Profissional.objects.create(usuario=user, telefone='11999999999', especialidade='Pilates', crefito='12345-F')
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def criar(self, valor):
        return self.client.post('/api/clinicas/', {'nome': 'Clínica A', 'endereco': 'Rua A, 1', 'valor_por_atendimento': valor})

    def test_aceita_valor_zero(self):
        response = self.criar('0.00')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_rejeita_valor_negativo(self):
        response = self.criar('-10.00')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['valor_por_atendimento'], ['O valor não pode ser negativo.'])


class ReceitaNaListagemDeClinicasTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dr_lista', password='x')
        self.profissional = Profissional.objects.create(
            usuario=self.user, telefone='1', especialidade='x', crefito='LISTA-F'
        )
        self.paciente = Paciente.objects.create(profissional=self.profissional, nome='P', cpf='1', telefone='1')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def criar_clinica(self, nome, valor):
        return Clinica.objects.create(profissional=self.profissional, nome=nome, endereco='Rua', valor_por_atendimento=Decimal(valor))

    def realizar(self, clinica, hora, experimental=False):
        return Agendamento.objects.create(
            profissional=self.profissional, clinica=clinica, paciente=self.paciente, data=date(2026, 3, 10),
            hora_inicio=time(hora, 0), hora_fim=time(hora + 1, 0), status='RE', eh_experimental=experimental,
        )

    def test_receita_usa_o_valor_congelado_e_nao_cobra_experimental(self):
        clinica = self.criar_clinica('Studio', '40.00')
        self.realizar(clinica, 8)
        self.realizar(clinica, 9, experimental=True)
        clinica.valor_por_atendimento = Decimal('60.00')
        clinica.save()

        item = self.client.get('/api/clinicas/').data['results'][0]

        self.assertEqual(item['receita_total'], Decimal('40.00'))
        self.assertEqual(item['total_atendimentos'], 2)

    def test_numero_de_consultas_nao_cresce_com_o_numero_de_clinicas(self):
        def consultas_da_listagem():
            with CaptureQueriesContext(connection) as contexto:
                self.client.get('/api/clinicas/')
            return len(contexto)

        self.realizar(self.criar_clinica('Clínica 1', '40.00'), 8)
        uma = consultas_da_listagem()
        for i in range(2, 6):
            self.realizar(self.criar_clinica(f'Clínica {i}', '50.00'), 8 + i)

        self.assertEqual(consultas_da_listagem(), uma)


class CorDaClinicaTestCase(TestCase):
    def setUp(self):
        self.profissional = self.criar_profissional('dr_cores')
        self.client = APIClient()
        self.client.force_authenticate(user=self.profissional.usuario)

    @staticmethod
    def criar_profissional(username):
        user = User.objects.create_user(username=username, password='x')
        return Profissional.objects.create(usuario=user, telefone='1', especialidade='x', crefito=f'{username}-F')

    def criar(self, profissional=None, nome='Clínica'):
        return Clinica.objects.create(
            profissional=profissional or self.profissional, nome=nome, endereco='Rua', valor_por_atendimento=Decimal('50.00')
        )

    def test_clinicas_do_mesmo_profissional_nao_repetem_cor(self):
        cores = [self.criar(nome=f'C{i}').cor for i in range(5)]

        self.assertEqual(cores, [1, 2, 3, 4, 5])

    def test_cada_profissional_tem_a_propria_paleta(self):
        self.criar()
        outro = self.criar_profissional('dr_outro')

        self.assertEqual(self.criar(profissional=outro).cor, 1)

    def test_acima_de_cinco_clinicas_reaproveita_a_cor_menos_usada(self):
        for i in range(5):
            self.criar(nome=f'C{i}')

        self.assertEqual(self.criar(nome='Sexta').cor, 1)
        self.assertEqual(self.criar(nome='Sétima').cor, 2)

    def test_cor_de_clinica_excluida_volta_a_ficar_livre(self):
        self.criar(nome='A')
        segunda = self.criar(nome='B')
        self.criar(nome='C')
        segunda.delete()

        self.assertEqual(self.criar(nome='D').cor, 2)

    def test_editar_a_clinica_nao_troca_a_cor(self):
        self.criar(nome='A')
        clinica = self.criar(nome='B')
        clinica.nome = 'B renomeada'
        clinica.save()

        clinica.refresh_from_db()
        self.assertEqual(clinica.cor, 2)

    def test_cor_e_escolhida_pelo_sistema_e_nao_pelo_cliente(self):
        response = self.client.post('/api/clinicas/', {
            'nome': 'Nova', 'endereco': 'Rua', 'valor_por_atendimento': '50.00', 'cor': 4,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cor'], 1)

    def test_cor_aparece_em_todas_as_telas_que_mostram_a_clinica(self):
        clinica = self.criar()
        clinica.cor = 3
        clinica.save()
        paciente = Paciente.objects.create(profissional=self.profissional, nome='P', cpf='1', telefone='1')
        Agendamento.objects.create(
            profissional=self.profissional, clinica=clinica, paciente=paciente, data=date(2026, 3, 10),
            hora_inicio=time(8, 0), hora_fim=time(9, 0), status='RE',
        )

        self.assertEqual(self.client.get('/api/clinicas/').data['results'][0]['cor'], 3)
        self.assertEqual(self.client.get('/api/clinicas/opcoes/').data[0]['cor'], 3)
        self.assertEqual(self.client.get('/api/agendamentos/?data_inicio=2026-03-10&data_fim=2026-03-10').data[0]['cor_clinica'], 3)
        resumo = self.client.get('/api/resumo-financeiro/?periodo=mes&data=2026-03-10').data
        self.assertEqual(resumo['por_clinica'][0]['clinica__cor'], 3)


class MigracaoDasCoresTestCase(TestCase):

    def test_mantem_a_cor_que_a_clinica_ja_mostrava_e_so_troca_as_repetidas(self):
        from importlib import import_module
        from django.apps import apps

        atribuir_cores = import_module('clinicas.migrations.0003_clinica_cor').atribuir_cores
        user = User.objects.create_user(username='dr_antigo', password='x')
        profissional = Profissional.objects.create(usuario=user, telefone='1', especialidade='x', crefito='ANTIGO-F')
        clinicas = [
            Clinica.objects.create(profissional=profissional, nome=f'C{i}', endereco='R', valor_por_atendimento=1, cor=1)
            for i in range(3)
        ]
        base = 1000
        for i, clinica in enumerate(clinicas):
            Clinica.objects.filter(pk=clinica.pk).update(id=base + [0, 5, 1][i])

        atribuir_cores(apps, None)

        cores = dict(Clinica.objects.values_list('id', 'cor'))
        self.assertEqual(cores[base], base % 5 + 1)
        self.assertEqual(cores[base + 1], (base + 1) % 5 + 1)
        self.assertEqual(len(set(cores.values())), 3)

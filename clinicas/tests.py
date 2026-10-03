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

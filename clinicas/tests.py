from django.contrib.auth.models import User
from django.test import TestCase
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

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from profissionais.models import Profissional


class LimitesDeTextoPacienteAPITestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='dr_silva', password='password123')
        Profissional.objects.create(usuario=user, telefone='11999999999', especialidade='Pilates', crefito='12345-F')
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def criar(self, **campos):
        dados = {'nome': 'Maria Souza', 'cpf': '111.111.111-11', 'telefone': '11911111111', **campos}
        return self.client.post('/api/pacientes/', dados)

    def test_historico_medico_aceita_ate_10000_caracteres(self):
        response = self.criar(historico_medico='a' * 10000)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_historico_medico_acima_de_10000_e_rejeitado(self):
        response = self.criar(historico_medico='a' * 10001)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('historico_medico', response.data)

    def test_endereco_acima_de_255_e_rejeitado(self):
        response = self.criar(endereco='a' * 256)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('endereco', response.data)

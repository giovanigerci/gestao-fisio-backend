from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class HealthCheckAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/health/'

    def test_responde_ok_sem_autenticacao(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_nao_consulta_o_banco(self):
        with self.assertNumQueries(0):
            self.client.get(self.url)

    def test_ignora_cookie_de_token_invalido(self):
        self.client.cookies['access_token'] = 'token-invalido'
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nao_pode_ser_cacheado(self):
        response = self.client.get(self.url)

        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_aceita_head(self):
        response = self.client.head(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apenas_leitura(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

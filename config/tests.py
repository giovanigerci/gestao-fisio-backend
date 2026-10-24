import io
import logging
from contextlib import ExitStack
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from config.views import HealthCheckView


class LogDeErrosTestCase(TestCase):
    """Os testes rodam com DEBUG=False, como em produção."""

    def requisitar_capturando_log(self, url, **patches):
        saida = io.StringIO()
        client = APIClient(raise_request_exception=False)
        manipuladores = [h for h in logging.getLogger('django').handlers if isinstance(h, logging.StreamHandler)]
        with ExitStack() as pilha:
            for manipulador in manipuladores:
                pilha.enter_context(patch.object(manipulador, 'stream', saida))
            for alvo, efeito in patches.items():
                pilha.enter_context(patch.object(HealthCheckView, alvo, side_effect=efeito))
            resposta = client.get(url)
        return resposta, saida.getvalue()

    def test_erro_500_aparece_no_log_com_o_traceback(self):
        resposta, log = self.requisitar_capturando_log('/api/health/', get=RuntimeError('falha simulada'))

        self.assertEqual(resposta.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('Internal Server Error: /api/health/', log)
        self.assertIn('RuntimeError: falha simulada', log)

    def test_respostas_4xx_nao_poluem_o_log(self):
        resposta, log = self.requisitar_capturando_log('/api/auth/me/')

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(log, '')


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
        self.client.cookies['access'] = 'token-invalido'
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


class VerificarOrigemTestCase(TestCase):
    URL = '/api/auth/logout/'

    def enviar(self, metodo='post', **cabecalhos):
        return getattr(APIClient(), metodo)(self.URL, **cabecalhos)

    def test_recusa_alteracao_vinda_de_outra_origem(self):
        resposta = self.enviar(HTTP_ORIGIN='https://outro.gestao-fisio.com')

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resposta.json(), {'detail': 'Origem não permitida.'})

    def test_aceita_a_origem_do_front(self):
        self.assertEqual(self.enviar(HTTP_ORIGIN='http://localhost:4200').status_code, status.HTTP_200_OK)

    def test_aceita_o_proprio_host_da_api(self):
        self.assertEqual(self.enviar(HTTP_ORIGIN='http://testserver').status_code, status.HTTP_200_OK)

    def test_sem_origin_passa(self):
        self.assertEqual(self.enviar().status_code, status.HTTP_200_OK)

    def test_leitura_de_outra_origem_nao_e_bloqueada_aqui(self):
        resposta = APIClient().get('/api/health/', HTTP_ORIGIN='https://outro.gestao-fisio.com')

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from profissionais.models import Profissional

SENHA = 'SenhaForte123'
NOVA_SENHA = 'OutraSenha456'


class SessaoTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('dra_ana', 'ana@exemplo.com', SENHA)
        Profissional.objects.create(usuario=self.user, telefone='11999999999', especialidade='Pilates', crefito='1234-F')

    def entrar(self, manter_conectado=False):
        client = APIClient()
        resposta = client.post(
            '/api/auth/token/', {'username': 'dra_ana', 'password': SENHA, 'manter_conectado': manter_conectado},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        return client, resposta

    def renovar(self, valor, nome='refresh'):
        client = APIClient()
        client.cookies[nome] = valor
        return client.post('/api/auth/token/refresh/')

    def trocar_senha(self, client):
        return client.post(
            '/api/auth/trocar-senha/',
            {'senha_atual': SENHA, 'nova_senha': NOVA_SENHA, 'confirmar_senha': NOVA_SENHA},
        )

    @override_settings(COOKIE_DOMAIN='.gestao-fisio.com')
    def test_login_grava_cookies_so_para_o_host_da_api_e_apaga_os_antigos(self):
        _, resposta = self.entrar()

        access, refresh = resposta.cookies['access'], resposta.cookies['refresh']
        self.assertEqual((access['path'], refresh['path']), ('/api/', '/api/auth/'))
        self.assertEqual((access['domain'], refresh['domain']), ('', ''))
        self.assertTrue(access['httponly'] and refresh['httponly'])

        for nome, caminho in (('access_token', '/api/'), ('refresh_token', '/api/auth/token/refresh/')):
            antigo = resposta.cookies[nome]
            self.assertEqual((antigo.value, antigo['max-age'], antigo['path']), ('', 0, caminho))
            self.assertEqual(antigo['domain'], '.gestao-fisio.com')

    def test_manter_conectado_dura_30_dias(self):
        _, resposta = self.entrar(manter_conectado=True)

        self.assertEqual(resposta.cookies['refresh']['max-age'], 30 * 24 * 60 * 60)

    def test_cookies_antigos_ainda_valem_durante_a_transicao(self):
        client = APIClient()
        client.cookies['access_token'] = str(RefreshToken.for_user(self.user).access_token)
        self.assertEqual(client.get('/api/auth/me/').status_code, status.HTTP_200_OK)

        resposta = self.renovar(str(RefreshToken.for_user(self.user)), nome='refresh_token')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.cookies['refresh'].value)
        self.assertEqual(resposta.cookies['refresh_token'].value, '')

    def test_refresh_so_vale_uma_vez(self):
        _, resposta = self.entrar()
        refresh = resposta.cookies['refresh'].value

        self.assertEqual(self.renovar(refresh).status_code, status.HTTP_200_OK)
        self.assertEqual(self.renovar(refresh).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalida_o_refresh(self):
        client, resposta = self.entrar()
        refresh = resposta.cookies['refresh'].value

        saida = client.post('/api/auth/logout/')

        self.assertEqual(saida.status_code, status.HTTP_200_OK)
        self.assertEqual(saida.cookies['refresh'].value, '')
        self.assertEqual(self.renovar(refresh).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_sem_sessao_responde_normalmente(self):
        self.assertEqual(APIClient().post('/api/auth/logout/').status_code, status.HTTP_200_OK)

    def test_trocar_senha_derruba_as_outras_sessoes_e_mantem_a_atual(self):
        _, no_celular = self.entrar()
        computador, _ = self.entrar()

        resposta = self.trocar_senha(computador)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.renovar(no_celular.cookies['refresh'].value).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.renovar(resposta.cookies['refresh'].value).status_code, status.HTTP_200_OK)

    def test_trocar_senha_mantem_a_duracao_da_sessao(self):
        client, _ = self.entrar(manter_conectado=True)

        resposta = self.trocar_senha(client)

        self.assertEqual(resposta.cookies['refresh']['max-age'], 30 * 24 * 60 * 60)

    def test_redefinir_senha_derruba_todas_as_sessoes(self):
        _, resposta = self.entrar()
        dados = {
            'uid': urlsafe_base64_encode(force_bytes(self.user.pk)),
            'token': default_token_generator.make_token(self.user),
            'nova_senha': NOVA_SENHA,
            'confirmar_senha': NOVA_SENHA,
        }

        self.assertEqual(APIClient().post('/api/auth/redefinir-senha/', dados).status_code, status.HTTP_200_OK)
        self.assertEqual(self.renovar(resposta.cookies['refresh'].value).status_code, status.HTTP_401_UNAUTHORIZED)


class LimiteDeTentativasDeLoginTestCase(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user('dra_ana', 'ana@exemplo.com', SENHA)

    def tentar(self, ip_forjado, usuario='dra_ana'):
        # O proxy acrescenta o IP real no fim; o começo do cabeçalho é o que o visitante mandou
        return APIClient().post(
            '/api/auth/token/', {'username': usuario, 'password': 'errada'},
            HTTP_X_FORWARDED_FOR=f'{ip_forjado}, 203.0.113.7',
        )

    def test_limite_por_conta_vale_mesmo_trocando_o_ip(self):
        for i in range(10):
            self.assertEqual(self.tentar(f'10.0.0.{i}').status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.tentar('10.0.0.99').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_limite_de_uma_conta_nao_afeta_outra(self):
        for i in range(10):
            self.tentar(f'10.0.0.{i}')

        self.assertEqual(self.tentar('10.0.0.50', usuario='outra').status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'NUM_PROXIES': 1})
    def test_com_num_proxies_forjar_o_ip_nao_escapa_do_limite(self):
        for i in range(5):
            self.assertEqual(self.tentar(f'10.0.0.{i}', usuario=f'conta{i}').status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(self.tentar('10.0.0.9', usuario='conta9').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_trocar_senha_tem_limite(self):
        usuario = User.objects.get(username='dra_ana')
        client = APIClient()
        client.force_authenticate(usuario)
        dados = {'senha_atual': 'errada', 'nova_senha': NOVA_SENHA, 'confirmar_senha': NOVA_SENHA}

        for _ in range(10):
            self.assertEqual(client.post('/api/auth/trocar-senha/', dados).status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(client.post('/api/auth/trocar-senha/', dados).status_code, status.HTTP_429_TOO_MANY_REQUESTS)

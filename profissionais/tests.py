import io
import re
import shutil
import smtplib
import tempfile
from unittest.mock import patch
from PIL import Image
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from profissionais.models import Profissional

MEDIA_ROOT_TESTE = tempfile.mkdtemp()


def gerar_imagem(formato='PNG', nome='foto.png', tamanho=(10, 10)):
    buffer = io.BytesIO()
    Image.new('RGB', tamanho, color='blue').save(buffer, format=formato)
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type=f'image/{formato.lower()}')


# Força o disco local mesmo com USE_S3=True no .env, para os testes nunca gravarem no bucket real
@override_settings(
    MEDIA_ROOT=MEDIA_ROOT_TESTE,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class FotoPerfilAPITestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT_TESTE, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='dr_silva', password='password123')
        self.profissional = Profissional.objects.create(
            usuario=self.user,
            telefone='11999999999',
            especialidade='Fisioterapia Geral',
            crefito='12345-F'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/auth/me/foto/'

    def test_upload_imagem_valida(self):
        response = self.client.post(self.url, {'foto': gerar_imagem(nome='Joao Silva.png')}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profissional.refresh_from_db()
        self.assertTrue(self.profissional.foto.storage.exists(self.profissional.foto.name))
        # Nome aleatório, sem o nome original do arquivo
        self.assertRegex(self.profissional.foto.name, r'^perfis/[0-9a-f]{32}\.png$')
        self.assertTrue(response.data['foto'].startswith('http://testserver/media/perfis/'))

        perfil = self.client.get('/api/auth/me/')
        self.assertEqual(perfil.data['foto'], response.data['foto'])

    def test_extensao_segue_formato_real(self):
        # PNG enviado com extensão .jpg é salvo como .png
        self.client.post(self.url, {'foto': gerar_imagem('PNG', nome='foto.jpg')}, format='multipart')

        self.profissional.refresh_from_db()
        self.assertTrue(self.profissional.foto.name.endswith('.png'))

    def test_sem_arquivo(self):
        response = self.client.post(self.url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['foto'], ['Nenhum arquivo enviado.'])

    def test_arquivo_que_nao_e_imagem(self):
        arquivo = SimpleUploadedFile('script.png', b'<script>alert(1)</script>', content_type='image/png')
        response = self.client.post(self.url, {'foto': arquivo}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.profissional.refresh_from_db()
        self.assertFalse(self.profissional.foto)

    def test_formato_nao_permitido(self):
        response = self.client.post(self.url, {'foto': gerar_imagem('GIF', nome='foto.gif')}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('JPEG, PNG ou WEBP', response.data['foto'][0])

    def test_arquivo_maior_que_5mb(self):
        imagem = gerar_imagem()
        conteudo = imagem.read() + b'\0' * (5 * 1024 * 1024)
        arquivo = SimpleUploadedFile('grande.png', conteudo, content_type='image/png')
        response = self.client.post(self.url, {'foto': arquivo}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['foto'], ['A imagem deve ter no máximo 5 MB.'])

    def test_nova_foto_remove_a_antiga(self):
        self.client.post(self.url, {'foto': gerar_imagem()}, format='multipart')
        self.profissional.refresh_from_db()
        foto_antiga = self.profissional.foto.name

        self.client.post(self.url, {'foto': gerar_imagem('JPEG', nome='nova.jpg')}, format='multipart')
        self.profissional.refresh_from_db()

        self.assertNotEqual(self.profissional.foto.name, foto_antiga)
        self.assertFalse(self.profissional.foto.storage.exists(foto_antiga))
        self.assertTrue(self.profissional.foto.storage.exists(self.profissional.foto.name))

    def test_upload_invalido_mantem_foto_atual(self):
        self.client.post(self.url, {'foto': gerar_imagem()}, format='multipart')
        self.profissional.refresh_from_db()
        foto_atual = self.profissional.foto.name

        self.client.post(self.url, {'foto': gerar_imagem('GIF', nome='foto.gif')}, format='multipart')
        self.profissional.refresh_from_db()

        self.assertEqual(self.profissional.foto.name, foto_atual)
        self.assertTrue(self.profissional.foto.storage.exists(foto_atual))

    def test_delete_remove_arquivo_do_storage(self):
        self.client.post(self.url, {'foto': gerar_imagem()}, format='multipart')
        self.profissional.refresh_from_db()
        nome = self.profissional.foto.name
        storage = self.profissional.foto.storage

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.profissional.refresh_from_db()
        self.assertFalse(self.profissional.foto)
        self.assertFalse(storage.exists(nome))


@override_settings(
    FRONTEND_URL='https://gestao-fisio.com/',
    DEFAULT_FROM_EMAIL='Gestão Fisio <nao-responda@gestao-fisio.com>',
)
class RecuperacaoSenhaAPITestCase(TestCase):
    MENSAGEM = 'Se o e-mail estiver cadastrado, você receberá um link de recuperação.'

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='dr_silva', email='joao@exemplo.com', password='SenhaAntiga@123'
        )
        self.client = APIClient()
        self.url_solicitar = '/api/auth/esqueci-senha/'
        self.url_redefinir = '/api/auth/redefinir-senha/'

    def extrair_uid_e_token(self, corpo):
        link = re.search(r'https://gestao-fisio\.com/redefinir-senha\?uid=(\S+)&token=(\S+)', corpo)
        self.assertIsNotNone(link, 'Link de redefinição não encontrado no e-mail')
        return link.group(1), link.group(2)

    def test_email_cadastrado_recebe_link(self):
        response = self.client.post(self.url_solicitar, {'email': 'JOAO@exemplo.com '})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], self.MENSAGEM)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['joao@exemplo.com'])
        self.assertEqual(mail.outbox[0].from_email, 'Gestão Fisio <nao-responda@gestao-fisio.com>')
        self.extrair_uid_e_token(mail.outbox[0].body)

    def test_email_nao_cadastrado_tem_mesma_resposta_e_nao_envia(self):
        response = self.client.post(self.url_solicitar, {'email': 'ninguem@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], self.MENSAGEM)
        self.assertEqual(len(mail.outbox), 0)

    def test_falha_no_envio_nao_revela_que_o_email_existe(self):
        with patch('profissionais.views_auth.send_mail', side_effect=smtplib.SMTPException('fora do ar')), \
                self.assertLogs('profissionais.views_auth', level='ERROR') as logs:
            response = self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], self.MENSAGEM)
        self.assertNotIn('joao@exemplo.com', ''.join(logs.output))

    def test_email_repetido_em_duas_contas_nao_quebra(self):
        User.objects.create_user(username='dr_silva_2', email='joao@exemplo.com', password='x')

        response = self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)

    def test_conta_inativa_nao_recebe_link(self):
        self.user.is_active = False
        self.user.save()

        self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})

        self.assertEqual(len(mail.outbox), 0)

    def test_fluxo_completo_redefine_senha_e_link_so_vale_uma_vez(self):
        self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})
        uid, token = self.extrair_uid_e_token(mail.outbox[0].body)
        dados = {'uid': uid, 'token': token, 'nova_senha': 'NovaSenha@456', 'confirmar_senha': 'NovaSenha@456'}

        response = self.client.post(self.url_redefinir, dados)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NovaSenha@456'))

        reuso = self.client.post(self.url_redefinir, dados)
        self.assertEqual(reuso.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_invalido_e_rejeitado(self):
        dados = {'uid': 'MQ', 'token': 'token-falso', 'nova_senha': 'NovaSenha@456', 'confirmar_senha': 'NovaSenha@456'}

        response = self.client.post(self.url_redefinir, dados)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('SenhaAntiga@123'))

    def test_limite_de_solicitacoes_por_hora(self):
        for _ in range(3):
            self.client.post(self.url_solicitar, {'email': 'ninguem@exemplo.com'})

        response = self.client.post(self.url_solicitar, {'email': 'ninguem@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

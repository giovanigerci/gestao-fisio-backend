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
from datetime import timedelta
from django.utils import timezone
from profissionais.models import CodigoVerificacaoEmail, Profissional
from profissionais.serializers import MENSAGEM_SENHA_FRACA

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

    def test_email_tem_versao_html_e_texto_com_o_link(self):
        self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})
        email = mail.outbox[0]
        html, tipo = email.alternatives[0]
        uid, token = self.extrair_uid_e_token(email.body)

        self.assertEqual(tipo, 'text/html')
        self.assertIn('Redefinir senha', html)
        self.assertIn('Olá, dr_silva!', html)
        # No HTML o "&" do link é escapado (correto em atributos); no texto puro, não
        self.assertIn(f'href="https://gestao-fisio.com/redefinir-senha?uid={uid}&amp;token={token}"', html)
        self.assertIn(f'?uid={uid}&token={token}', email.body)
        self.assertNotIn('&amp;', email.body)
        self.assertIn('src="https://gestao-fisio.com/logo.png"', html)

    def test_nome_com_html_e_escapado_no_email(self):
        self.user.first_name = '<b>Maria</b>'
        self.user.save()

        self.client.post(self.url_solicitar, {'email': 'joao@exemplo.com'})
        html, _ = mail.outbox[0].alternatives[0]

        self.assertIn('Olá, &lt;b&gt;Maria&lt;/b&gt;!', html)
        self.assertNotIn('<b>Maria</b>', html)

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


class CadastroComCodigoAPITestCase(TestCase):
    def setUp(self):
        cache.clear()  # throttles ficam no cache
        self.client = APIClient()
        self.url_codigo = '/api/auth/registrar/enviar-codigo/'
        self.url_registrar = '/api/auth/registrar/'
        self.dados = {
            'username': 'dr_novo',
            'email': 'Novo@Exemplo.com',
            'password': 'SenhaForte@123',
            'telefone': '11999999999',
            'especialidade': 'Ortopedia',
            'crefito': '99999-F',
        }

    def enviar_codigo(self, **alteracoes):
        return self.client.post(self.url_codigo, {**self.dados, **alteracoes})

    def codigo_do_ultimo_email(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def codigo_diferente(self, codigo):
        return '000000' if codigo != '000000' else '111111'

    def voltar_relogio_do_codigo(self, minutos):
        CodigoVerificacaoEmail.objects.update(criado_em=timezone.now() - timedelta(minutes=minutos))


    def test_envia_codigo_sem_criar_a_conta(self):
        response = self.enviar_codigo()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['novo@exemplo.com'])
        codigo = self.codigo_do_ultimo_email()
        self.assertIn(codigo, mail.outbox[0].subject)
        self.assertIn(codigo, mail.outbox[0].alternatives[0][0])
        self.assertFalse(User.objects.filter(username='dr_novo').exists())

    def test_codigo_nao_fica_salvo_em_texto_puro(self):
        self.enviar_codigo()

        registro = CodigoVerificacaoEmail.objects.get()
        self.assertNotIn(self.codigo_do_ultimo_email(), registro.codigo_hash)

    def test_email_e_obrigatorio(self):
        dados = {k: v for k, v in self.dados.items() if k != 'email'}
        response = self.client.post(self.url_codigo, dados)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_ja_em_uso_ignorando_maiusculas(self):
        User.objects.create_user(username='outro', email='novo@exemplo.com', password='x')

        response = self.enviar_codigo(email='NOVO@exemplo.com')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'], ['Este e-mail já está em uso.'])

    def test_senha_fraca_mostra_uma_unica_mensagem_com_os_requisitos(self):
        # "123" falha em 3 validadores, mas o usuário vê uma só mensagem dizendo o que fazer
        response = self.enviar_codigo(password='123')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['password'], [MENSAGEM_SENHA_FRACA])
        self.assertEqual(len(mail.outbox), 0)

    def test_senha_precisa_de_letras_e_numeros(self):
        for senha in ('somenteletras', '84736251'):
            with self.subTest(senha=senha):
                response = self.enviar_codigo(password=senha)
                self.assertEqual(response.data['password'], [MENSAGEM_SENHA_FRACA])

    def test_senha_acima_de_128_caracteres_e_rejeitada(self):
        response = self.enviar_codigo(password='Senha1' + 'a' * 123)  # 129 caracteres

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_senha_com_letras_e_numeros_sem_simbolo_e_aceita(self):
        response = self.enviar_codigo(password='fisioterapia2026')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reenvio_so_depois_do_intervalo_e_invalida_o_codigo_anterior(self):
        self.enviar_codigo()
        primeiro = self.codigo_do_ultimo_email()

        cedo = self.enviar_codigo()
        self.assertEqual(cedo.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertGreater(cedo.data['aguardar_segundos'], 0)

        self.voltar_relogio_do_codigo(minutos=2)
        self.assertEqual(self.enviar_codigo().status_code, status.HTTP_200_OK)
        self.assertEqual(CodigoVerificacaoEmail.objects.count(), 1)
        if primeiro != self.codigo_do_ultimo_email():
            response = self.client.post(self.url_registrar, {**self.dados, 'codigo': primeiro})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_falha_no_envio_remove_o_codigo_para_tentar_de_novo(self):
        with patch('profissionais.views.send_mail', side_effect=smtplib.SMTPException('fora do ar')), \
                self.assertLogs('profissionais.views', level='ERROR'):
            response = self.enviar_codigo()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(CodigoVerificacaoEmail.objects.exists())
        self.assertEqual(self.enviar_codigo().status_code, status.HTTP_200_OK)


    def test_codigo_certo_cria_a_conta_com_o_email(self):
        self.enviar_codigo()

        response = self.client.post(self.url_registrar, {**self.dados, 'codigo': self.codigo_do_ultimo_email()})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='dr_novo')
        self.assertEqual(user.email, 'novo@exemplo.com')
        self.assertTrue(user.check_password('SenhaForte@123'))
        self.assertTrue(Profissional.objects.filter(usuario=user, crefito='99999-F').exists())
        self.assertFalse(CodigoVerificacaoEmail.objects.exists())

    def test_sem_codigo_nao_cria_a_conta(self):
        response = self.client.post(self.url_registrar, self.dados)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('codigo', response.data)
        self.assertFalse(User.objects.filter(username='dr_novo').exists())

    def test_codigo_errado_nao_cria_a_conta(self):
        self.enviar_codigo()
        errado = self.codigo_diferente(self.codigo_do_ultimo_email())

        response = self.client.post(self.url_registrar, {**self.dados, 'codigo': errado})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['codigo'], ['Código inválido ou expirado.'])
        self.assertFalse(User.objects.filter(username='dr_novo').exists())

    def test_codigo_expirado_nao_cria_a_conta(self):
        self.enviar_codigo()
        codigo = self.codigo_do_ultimo_email()
        self.voltar_relogio_do_codigo(minutos=11)

        response = self.client.post(self.url_registrar, {**self.dados, 'codigo': codigo})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='dr_novo').exists())

    def test_codigo_bloqueia_apos_5_tentativas_erradas(self):
        self.enviar_codigo()
        codigo = self.codigo_do_ultimo_email()
        for _ in range(CodigoVerificacaoEmail.MAX_TENTATIVAS):
            CodigoVerificacaoEmail.verificar('novo@exemplo.com', self.codigo_diferente(codigo))

        response = self.client.post(self.url_registrar, {**self.dados, 'codigo': codigo})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='dr_novo').exists())

    def test_codigo_de_outro_email_nao_serve(self):
        self.enviar_codigo(email='outro@exemplo.com', username='dr_outro', crefito='88888-F')
        codigo_do_outro = self.codigo_do_ultimo_email()

        response = self.client.post(self.url_registrar, {**self.dados, 'codigo': codigo_do_outro})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='dr_novo').exists())


class EmailUnicoNoPerfilAPITestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username='outro', email='ocupado@exemplo.com', password='x')
        self.user = User.objects.create_user(username='dr_silva', email='joao@exemplo.com', password='x')
        Profissional.objects.create(usuario=self.user, telefone='1', especialidade='x', crefito='12345-F')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_nao_permite_email_de_outra_conta(self):
        response = self.client.patch('/api/auth/me/', {'email': 'OCUPADO@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'], ['Este e-mail já está em uso.'])

    def test_permite_manter_o_proprio_email(self):
        response = self.client.patch('/api/auth/me/', {'email': 'JOAO@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'joao@exemplo.com')

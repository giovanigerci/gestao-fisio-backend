import io
import re
import shutil
import smtplib
import tempfile
import zipfile
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from PIL import Image
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from datetime import timedelta
from django.utils import timezone
from agenda.models import Agendamento
from clinicas.models import Clinica
from pacientes.models import Paciente
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
        self.assertRegex(self.profissional.foto.name, r'^perfis/[0-9a-f]{32}\.webp$')
        self.assertTrue(response.data['foto'].startswith('http://testserver/media/perfis/'))

        perfil = self.client.get('/api/auth/me/')
        self.assertEqual(perfil.data['foto'], response.data['foto'])

    def enviar_e_abrir(self, arquivo):
        self.assertEqual(self.client.post(self.url, {'foto': arquivo}, format='multipart').status_code, status.HTTP_200_OK)
        self.profissional.refresh_from_db()
        with self.profissional.foto.open('rb') as salvo:
            imagem = Image.open(salvo)
            imagem.load()
        return imagem

    def test_salva_sempre_em_webp(self):
        imagem = self.enviar_e_abrir(gerar_imagem('JPEG', nome='foto.jpg'))

        self.assertEqual(imagem.format, 'WEBP')
        self.assertTrue(self.profissional.foto.name.endswith('.webp'))

    def test_reduz_para_no_maximo_256px_mantendo_a_proporcao(self):
        self.assertEqual(self.enviar_e_abrir(gerar_imagem(tamanho=(1000, 600))).size, (256, 154))

    def test_imagem_pequena_nao_e_ampliada(self):
        self.assertEqual(self.enviar_e_abrir(gerar_imagem(tamanho=(40, 30))).size, (40, 30))

    def test_remove_os_metadados_exif(self):
        exif = Image.Exif()
        exif[0x010F] = 'Celular de teste'  # Make
        exif[0x8825] = {2: (23.0, 33.0, 0.0)}  # GPSInfo: latitude
        buffer = io.BytesIO()
        Image.new('RGB', (50, 50), 'blue').save(buffer, format='JPEG', exif=exif)
        arquivo = SimpleUploadedFile('foto.jpg', buffer.getvalue(), content_type='image/jpeg')

        self.assertEqual(dict(self.enviar_e_abrir(arquivo).getexif()), {})

    def test_gira_conforme_a_orientacao_do_exif(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation: girar 90° (foto de celular "deitada")
        buffer = io.BytesIO()
        Image.new('RGB', (80, 40), 'blue').save(buffer, format='JPEG', exif=exif)
        arquivo = SimpleUploadedFile('foto.jpg', buffer.getvalue(), content_type='image/jpeg')

        self.assertEqual(self.enviar_e_abrir(arquivo).size, (40, 80))

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
                self.assertLogs('profissionais.views', level='ERROR'), \
                self.assertLogs('django.request', level='ERROR'):
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


class TrocaDeEmailAPITestCase(TestCase):
    SENHA = 'SenhaForte123'

    def setUp(self):
        cache.clear()
        User.objects.create_user(username='outro', email='ocupado@exemplo.com', password='x')
        self.user = User.objects.create_user(username='dr_silva', email='joao@exemplo.com', password=self.SENHA)
        Profissional.objects.create(usuario=self.user, telefone='1', especialidade='x', crefito='12345-F')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def solicitar(self, email='novo@exemplo.com', senha=None):
        return self.client.post('/api/auth/me/email/', {'email': email, 'senha_atual': senha or self.SENHA})

    def confirmar(self, codigo, email='novo@exemplo.com', client=None):
        return (client or self.client).post('/api/auth/me/email/confirmar/', {'email': email, 'codigo': codigo})

    def codigo_enviado(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def email_atual(self):
        self.user.refresh_from_db()
        return self.user.email

    def test_patch_do_perfil_nao_troca_o_email(self):
        response = self.client.patch('/api/auth/me/', {'email': 'novo@exemplo.com'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Alterar e-mail', response.data['email'][0])
        self.assertEqual(self.email_atual(), 'joao@exemplo.com')

    def test_patch_com_o_mesmo_email_continua_aceito(self):
        self.assertEqual(self.client.patch('/api/auth/me/', {'email': 'JOAO@exemplo.com'}).status_code, status.HTTP_200_OK)

    def test_fluxo_completo_envia_codigo_ao_novo_email_e_avisa_o_antigo(self):
        self.assertEqual(self.solicitar('Novo@Exemplo.com ').status_code, status.HTTP_200_OK)
        self.assertEqual(mail.outbox[0].to, ['novo@exemplo.com'])
        self.assertEqual(self.email_atual(), 'joao@exemplo.com')

        response = self.confirmar(self.codigo_enviado())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'novo@exemplo.com')
        self.assertEqual(self.email_atual(), 'novo@exemplo.com')
        self.assertEqual(mail.outbox[-1].to, ['joao@exemplo.com'])
        self.assertIn('novo@exemplo.com', mail.outbox[-1].body)

    def test_exige_a_senha_atual(self):
        response = self.solicitar(senha='errada')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['senha_atual'], ['Senha atual incorreta.'])
        self.assertEqual(len(mail.outbox), 0)

    def test_nao_permite_email_de_outra_conta(self):
        response = self.solicitar('OCUPADO@exemplo.com')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['email'], ['Este e-mail já está em uso.'])

    def test_nao_permite_o_proprio_email(self):
        self.assertEqual(self.solicitar('joao@exemplo.com').data['email'], ['Este já é o e-mail da sua conta.'])

    def test_codigo_errado_nao_troca(self):
        self.solicitar()

        response = self.confirmar('000000' if self.codigo_enviado() != '000000' else '111111')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.email_atual(), 'joao@exemplo.com')

    def test_codigo_de_um_usuario_nao_serve_para_outro(self):
        self.solicitar()
        codigo = self.codigo_enviado()
        outro = User.objects.get(username='outro')
        Profissional.objects.create(usuario=outro, telefone='1', especialidade='x', crefito='999-F')
        client_outro = APIClient()
        client_outro.force_authenticate(user=outro)

        self.assertEqual(self.confirmar(codigo, client=client_outro).status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_de_troca_nao_serve_para_cadastro(self):
        self.solicitar()

        self.assertFalse(CodigoVerificacaoEmail.verificar('novo@exemplo.com', self.codigo_enviado()))

    def test_reenvio_so_depois_de_60_segundos(self):
        self.solicitar()

        response = self.solicitar()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('aguardar_segundos', response.data)

    def test_exige_login(self):
        self.assertEqual(APIClient().post('/api/auth/me/email/', {}).status_code, status.HTTP_401_UNAUTHORIZED)


class BaseDadosDaContaTestCase(TestCase):
    """Dois profissionais com dados próprios: o que um faz não pode alcançar o outro."""

    SENHA = 'SenhaForte123'

    def setUp(self):
        cache.clear()  # zera os contadores de throttle entre os testes
        self.user, self.profissional = self.criar_profissional('dra_ana', 'ana@exemplo.com', 'ANA-F')
        self.outro_user, self.outro = self.criar_profissional('dr_bruno', 'bruno@exemplo.com', 'BRUNO-F')
        self.clinica, self.paciente, self.sessao = self.criar_dados(self.profissional, 'Ana')
        self.criar_dados(self.outro, 'Bruno')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def criar_profissional(self, username, email, crefito):
        user = User.objects.create_user(username=username, email=email, password=self.SENHA, first_name=username)
        profissional = Profissional.objects.create(
            usuario=user, telefone='11999999999', especialidade='Pilates', crefito=crefito
        )
        return user, profissional

    @staticmethod
    def criar_dados(profissional, sufixo):
        clinica = Clinica.objects.create(
            profissional=profissional, nome=f'Clínica {sufixo}', endereco='Rua A, 1', valor_por_atendimento=Decimal('80.00')
        )
        paciente = Paciente.objects.create(
            profissional=profissional, nome=f'Paciente {sufixo}', cpf='123.456.789-00', telefone='11988887777',
            data_nascimento=date(1990, 5, 20), historico_medico=f'Histórico de {sufixo}',
        )
        sessao = Agendamento.objects.create(
            profissional=profissional, clinica=clinica, paciente=paciente, data=date(2026, 3, 10),
            hora_inicio=time(8, 0), hora_fim=time(9, 0), status='RE',
        )
        return clinica, paciente, sessao

    @staticmethod
    def registros(profissional_id):
        return (
            Clinica.objects.filter(profissional_id=profissional_id).count(),
            Paciente.objects.filter(profissional_id=profissional_id).count(),
            Agendamento.objects.filter(profissional_id=profissional_id).count(),
        )


class ExportacaoDeDadosAPITestCase(BaseDadosDaContaTestCase):
    URL = '/api/auth/me/exportar/'

    def pacote(self):
        return zipfile.ZipFile(io.BytesIO(self.client.get(self.URL).content))

    def arquivos(self):
        pacote = self.pacote()
        return {nome: pacote.read(nome).decode('utf-8-sig') for nome in pacote.namelist()}

    def test_devolve_um_zip_com_todas_as_planilhas(self):
        response = self.client.get(self.URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('attachment; filename="gestao-fisio-dados-', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(
            sorted(zipfile.ZipFile(io.BytesIO(response.content)).namelist()),
            ['LEIAME.txt', 'agendamentos.csv', 'clinicas.csv', 'pacientes.csv', 'perfil.csv'],
        )

    def test_planilhas_trazem_os_dados_em_formato_que_o_excel_abre(self):
        arquivos = self.arquivos()

        self.assertIn('Nome;CPF;Telefone;E-mail;Data de nascimento;Endereço;Histórico médico', arquivos['pacientes.csv'])
        self.assertIn('Paciente Ana;123.456.789-00;11988887777;;20/05/1990;;Histórico de Ana', arquivos['pacientes.csv'])
        self.assertIn('Clínica Ana;Rua A, 1;;80,00;Sim', arquivos['clinicas.csv'])
        self.assertIn(
            '10/03/2026;08:00;09:00;Paciente Ana;123.456.789-00;Clínica Ana;Realizado;Não;80,00',
            arquivos['agendamentos.csv'],
        )
        self.assertIn('ana@exemplo.com', arquivos['perfil.csv'])

    def test_arquivo_comeca_com_bom_para_o_excel_reconhecer_os_acentos(self):
        self.assertTrue(self.pacote().read('pacientes.csv').startswith(b'\xef\xbb\xbf'))

    def test_exporta_so_os_dados_do_proprio_profissional(self):
        tudo = '\n'.join(self.arquivos().values())

        self.assertIn('Paciente Ana', tudo)
        self.assertNotIn('Bruno', tudo)
        self.assertNotIn('bruno@exemplo.com', tudo)

    def test_texto_que_parece_formula_e_neutralizado(self):
        self.paciente.nome = '+55 Nome'
        self.paciente.historico_medico = '=HYPERLINK("http://malicioso";"clique")'
        self.paciente.save()

        planilha = self.arquivos()['pacientes.csv']

        self.assertIn("'+55 Nome", planilha)
        self.assertIn("'=HYPERLINK", planilha)

    def test_numero_de_consultas_nao_cresce_com_o_volume_de_dados(self):
        def consultas():
            with CaptureQueriesContext(connection) as contexto:
                self.client.get(self.URL)
            return len(contexto)

        antes = consultas()
        for i in range(5):
            paciente = Paciente.objects.create(profissional=self.profissional, nome=f'Extra {i}', cpf=str(i), telefone='1')
            Agendamento.objects.create(
                profissional=self.profissional, clinica=self.clinica, paciente=paciente, data=date(2026, 4, 1 + i),
                hora_inicio=time(8, 0), hora_fim=time(9, 0),
            )

        self.assertEqual(consultas(), antes)

    def test_resumo_conta_so_os_registros_proprios(self):
        response = self.client.get('/api/auth/me/dados/')

        self.assertEqual(response.data, {'clinicas': 1, 'pacientes': 1, 'agendamentos': 1})

    def test_exige_login(self):
        anonimo = APIClient()

        self.assertEqual(anonimo.get(self.URL).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(anonimo.get('/api/auth/me/dados/').status_code, status.HTTP_401_UNAUTHORIZED)


# Força o disco local mesmo com USE_S3=True no .env, para os testes nunca tocarem no bucket real
@override_settings(
    MEDIA_ROOT=MEDIA_ROOT_TESTE,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ExclusaoDeContaAPITestCase(BaseDadosDaContaTestCase):
    URL = '/api/auth/excluir-conta/'

    def excluir(self, senha=None, client=None):
        return (client or self.client).post(self.URL, {'senha': senha or self.SENHA})

    def test_senha_errada_nao_apaga_nada(self):
        response = self.excluir('senha-errada')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['senha'], ['Senha incorreta.'])
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(self.registros(self.profissional.id), (1, 1, 1))
        self.assertEqual(len(mail.outbox), 0)

    def test_sem_senha_nao_apaga_nada(self):
        response = self.client.post(self.URL, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_apaga_a_conta_e_tudo_o_que_e_dela(self):
        profissional_id = self.profissional.id

        response = self.excluir()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Profissional.objects.filter(pk=profissional_id).exists())
        self.assertEqual(self.registros(profissional_id), (0, 0, 0))

    def test_nao_toca_nos_dados_de_outro_profissional(self):
        self.excluir()

        self.assertTrue(User.objects.filter(pk=self.outro_user.pk).exists())
        self.assertEqual(self.registros(self.outro.id), (1, 1, 1))

    def test_apaga_a_foto_do_armazenamento(self):
        self.profissional.foto = gerar_imagem()
        self.profissional.save()
        caminho, armazenamento = self.profissional.foto.name, self.profissional.foto.storage
        self.assertTrue(armazenamento.exists(caminho))

        with self.captureOnCommitCallbacks(execute=True):
            self.excluir()

        self.assertFalse(armazenamento.exists(caminho))

    def test_limpa_os_cookies_de_sessao(self):
        response = self.excluir()

        self.assertEqual(response.cookies['access'].value, '')
        self.assertEqual(response.cookies['refresh'].value, '')

    def test_sessao_antiga_deixa_de_funcionar(self):
        navegador = APIClient()
        login = navegador.post('/api/auth/token/', {'username': 'dra_ana', 'password': self.SENHA})
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        refresh_antigo = login.cookies['refresh'].value
        self.assertTrue(OutstandingToken.objects.filter(user=self.user).exists())

        self.assertEqual(self.excluir(client=navegador).status_code, status.HTTP_200_OK)

        self.assertFalse(OutstandingToken.objects.filter(user_id=self.user.pk).exists())
        outro_navegador = APIClient()
        outro_navegador.cookies['refresh'] = refresh_antigo
        self.assertEqual(outro_navegador.post('/api/auth/token/refresh/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_avisa_por_email(self):
        self.excluir()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ana@exemplo.com'])
        self.assertIn('excluída', mail.outbox[0].subject)
        self.assertIn('definitiva', mail.outbox[0].body)

    def test_conta_sem_email_e_excluida_sem_aviso(self):
        User.objects.filter(pk=self.user.pk).update(email='')
        self.user.refresh_from_db()
        self.client.force_authenticate(user=self.user)

        self.assertEqual(self.excluir().status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_falha_no_email_nao_impede_a_exclusao(self):
        with patch('profissionais.views_dados.send_mail', side_effect=smtplib.SMTPException('fora do ar')), \
                self.assertLogs('profissionais.views_dados', level='ERROR'):
            response = self.excluir()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_limita_tentativas_de_senha(self):
        for _ in range(5):
            self.assertEqual(self.excluir('errada').status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.excluir('errada').status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_exige_login(self):
        resposta = APIClient().post(self.URL, {'senha': self.SENHA})

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

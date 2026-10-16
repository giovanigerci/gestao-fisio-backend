import datetime
import logging
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import ScopedRateThrottle

from .cookies import (
    DURACAO_REFRESH, DURACAO_REFRESH_LONGA, definir_cookies_de_sessao, ler_refresh, remover_cookies_de_sessao,
)
from .serializers import TrocarSenhaSerializer, RedefinirSenhaSerializer, FotoPerfilSerializer
from .throttling import LoginPorContaThrottle

logger = logging.getLogger(__name__)


def novo_refresh(usuario, sessao_longa):
    refresh = RefreshToken.for_user(usuario)
    if sessao_longa:
        refresh.set_exp(lifetime=datetime.timedelta(seconds=DURACAO_REFRESH_LONGA))
    return refresh


def e_sessao_longa(refresh):
    expira_em = datetime.datetime.fromtimestamp(refresh['exp'], tz=datetime.timezone.utc)
    return expira_em - timezone.now() > datetime.timedelta(seconds=DURACAO_REFRESH)


def revogar_sessoes(usuario):
    pendentes = OutstandingToken.objects.filter(user=usuario, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=token) for token in pendentes], ignore_conflicts=True)


class LoginCookieView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle, LoginPorContaThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        logger.warning(
            'Diagnóstico de IP (temporário): X-Forwarded-For=%r REMOTE_ADDR=%r CF-Connecting-IP=%r True-Client-IP=%r',
            request.META.get('HTTP_X_FORWARDED_FOR'), request.META.get('REMOTE_ADDR'),
            request.META.get('HTTP_CF_CONNECTING_IP'), request.META.get('HTTP_TRUE_CLIENT_IP'),
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manter_conectado = bool(request.data.get('manter_conectado', False))
        refresh = novo_refresh(serializer.user, manter_conectado)
        return definir_cookies_de_sessao(Response({'detail': 'Login realizado com sucesso.'}), refresh, manter_conectado)


class RefreshCookieView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        valor = ler_refresh(request)
        if not valor:
            raise AuthenticationFailed('Refresh token não encontrado.')

        try:
            token_antigo = RefreshToken(valor)
        except (InvalidToken, TokenError):
            raise AuthenticationFailed('Token inválido ou expirado.')

        try:
            user = User.objects.get(id=token_antigo.get('user_id'))
        except User.DoesNotExist:
            raise AuthenticationFailed('Usuário não encontrado.')

        sessao_longa = e_sessao_longa(token_antigo)
        token_antigo.blacklist()
        return definir_cookies_de_sessao(
            Response({'detail': 'Token renovado com sucesso.'}), novo_refresh(user, sessao_longa), sessao_longa,
        )


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        valor = ler_refresh(request)
        if valor:
            try:
                RefreshToken(valor).blacklist()
            except (InvalidToken, TokenError):
                pass
        return remover_cookies_de_sessao(Response({'detail': 'Logout realizado com sucesso.'}))

class FotoPerfilView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = FotoPerfilSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profissional = request.user.profissional
        foto_antiga = profissional.foto.name if profissional.foto else None

        profissional.foto = serializer.validated_data['foto']
        profissional.save(update_fields=['foto'])

        # Só remove a foto antiga depois que a nova foi salva com sucesso
        if foto_antiga:
            profissional.foto.storage.delete(foto_antiga)

        # build_absolute_uri mantém URLs já absolutas (R2) e completa as relativas (disco local)
        url = request.build_absolute_uri(profissional.foto.url)
        return Response({'foto': url})

    def delete(self, request):
        profissional = request.user.profissional
        if profissional.foto:
            profissional.foto.delete(save=True)
        return Response(status=204)


class TrocarSenhaView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'trocar_senha'

    def post(self, request):
        serializer = TrocarSenhaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['nova_senha'])
        user.save()

        sessao_longa = self._sessao_atual_e_longa(request)
        revogar_sessoes(user)
        return definir_cookies_de_sessao(
            Response({'detail': 'Senha alterada com sucesso.'}), novo_refresh(user, sessao_longa), sessao_longa,
        )

    @staticmethod
    def _sessao_atual_e_longa(request):
        valor = ler_refresh(request)
        if not valor:
            return False
        try:
            return e_sessao_longa(RefreshToken(valor))
        except (InvalidToken, TokenError):
            return False


class SolicitarResetSenhaView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        email = request.data.get('email', '').strip().lower()

        # Sempre retorna 200 para não revelar se o e-mail existe (anti-enumeração)
        resposta = Response({'detail': 'Se o e-mail estiver cadastrado, você receberá um link de recuperação.'})

        if not email:
            return resposta

        for user in User.objects.filter(email__iexact=email, is_active=True):
            self._enviar_link(user)

        return resposta

    def _enviar_link(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        site_url = settings.FRONTEND_URL.rstrip('/')
        contexto = {
            'nome': user.get_full_name() or user.username,
            'link': f'{site_url}/redefinir-senha?uid={uid}&token={token}',
            'site_url': site_url,
        }

        try:
            send_mail(
                subject='Recuperação de Senha — Gestão Fisio',
                # Texto puro + HTML: clientes sem suporte a HTML (e filtros de spam) usam o texto
                message=render_to_string('emails/redefinir_senha.txt', contexto),
                html_message=render_to_string('emails/redefinir_senha.html', contexto),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except Exception:
            logger.exception('Falha ao enviar e-mail de redefinição de senha (user_id=%s)', user.pk)


class RedefinirSenhaView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'redefinir_senha'

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')

        # Decodifica o uid para obter o usuário
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'Link de recuperação inválido ou expirado.'},
                status=400
            )

        # Valida o token
        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Link de recuperação inválido ou expirado.'},
                status=400
            )

        # Valida as senhas
        serializer = RedefinirSenhaSerializer(
            data=request.data,
            context={'user': user}
        )
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['nova_senha'])
        user.save()
        revogar_sessoes(user)

        return Response({'detail': 'Senha redefinida com sucesso.'})
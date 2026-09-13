import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import ScopedRateThrottle

from .serializers import TrocarSenhaSerializer, RedefinirSenhaSerializer


class LoginCookieView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data['access']
        refresh = serializer.validated_data['refresh']
        manter_conectado = request.data.get('manter_conectado', False)

        response = Response({'detail': 'Login realizado com sucesso.'})

        response.set_cookie(
            key='access_token',
            value=str(access),
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=5 * 60,
            path='/api/',
        )

        max_age_refresh = 30 * 24 * 60 * 60 if manter_conectado else 24 * 60 * 60
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=max_age_refresh,
            path='/api/auth/token/refresh/',
        )

        return response


class RefreshCookieView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            raise AuthenticationFailed('Refresh token não encontrado.')

        serializer = self.get_serializer(data={'refresh': refresh_token})
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data['access']

        token_antigo = RefreshToken(refresh_token)
        expira_em = datetime.datetime.fromtimestamp(token_antigo['exp'], tz=datetime.timezone.utc)
        tempo_restante = expira_em - timezone.now()
        sessao_longa = tempo_restante > datetime.timedelta(hours=24)

        response = Response({'detail': 'Token renovado com sucesso.'})
        response.set_cookie(
            key='access_token', value=str(access), httponly=True, secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE, max_age=5 * 60, path='/api/',
        )

        if sessao_longa:
            novo_refresh = RefreshToken.for_user(request.user)
            response.set_cookie(
                key='refresh_token', value=str(novo_refresh), httponly=True, secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE, max_age=30 * 24 * 60 * 60, path='/api/auth/token/refresh/',
            )

        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({'detail': 'Logout realizado com sucesso.'})
        response.delete_cookie('access_token', path='/api/')
        response.delete_cookie('refresh_token', path='/api/auth/token/refresh/')
        return response

class FotoPerfilView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profissional = request.user.profissional
        foto = request.FILES.get('foto')

        if not foto:
            return Response({'foto': 'Nenhum arquivo enviado.'}, status=400)

        if profissional.foto:
            profissional.foto.delete(save=False)

        profissional.foto = foto
        profissional.save()

        url = request.build_absolute_uri(profissional.foto.url)
        return Response({'foto': url})

    def delete(self, request):
        profissional = request.user.profissional
        if profissional.foto:
            profissional.foto.delete(save=True)
        return Response(status=204)


class TrocarSenhaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TrocarSenhaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['nova_senha'])
        user.save()

        return Response({'detail': 'Senha alterada com sucesso.'})


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

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return resposta

        # Gera uid e token seguros
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Constrói link para o frontend
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        link = f'{frontend_url}/redefinir-senha?uid={uid}&token={token}'

        # Envia e-mail
        send_mail(
            subject='Recuperação de Senha — Gestão Fisio',
            message=(
                f'Olá, {user.get_full_name() or user.username}!\n\n'
                f'Recebemos uma solicitação para redefinir a senha da sua conta.\n\n'
                f'Clique no link abaixo para criar uma nova senha:\n'
                f'{link}\n\n'
                f'Se você não solicitou essa alteração, ignore este e-mail.\n'
                f'O link expira automaticamente após o uso.\n\n'
                f'— Equipe Gestão Fisio'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return resposta


class RedefinirSenhaView(APIView):
    permission_classes = [AllowAny]

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

        # Atualiza a senha (isso invalida o token automaticamente)
        user.set_password(serializer.validated_data['nova_senha'])
        user.save()

        return Response({'detail': 'Senha redefinida com sucesso.'})
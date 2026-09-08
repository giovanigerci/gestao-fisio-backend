import datetime
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser


class LoginCookieView(TokenObtainPairView):
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
            samesite='Lax',
            max_age=5 * 60,
            path='/api/',
        )

        max_age_refresh = 30 * 24 * 60 * 60 if manter_conectado else 24 * 60 * 60
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite='Lax',
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
            samesite='Lax', max_age=5 * 60, path='/api/',
        )

        if sessao_longa:
            novo_refresh = RefreshToken.for_user(request.user)
            response.set_cookie(
                key='refresh_token', value=str(novo_refresh), httponly=True, secure=settings.COOKIE_SECURE,
                samesite='Lax', max_age=30 * 24 * 60 * 60, path='/api/auth/token/refresh/',
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
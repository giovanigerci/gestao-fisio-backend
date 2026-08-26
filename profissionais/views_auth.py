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

        response = Response({'detail': 'Login realizado com sucesso.'})

        response.set_cookie(
            key='access_token',
            value=str(access),
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=5 * 60,
            path='/api/',
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=24 * 60 * 60,
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

        response = Response({'detail': 'Token renovado com sucesso.'})
        response.set_cookie(
            key='access_token',
            value=str(access),
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=5 * 60,
            path='/api/',
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
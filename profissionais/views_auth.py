from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed


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
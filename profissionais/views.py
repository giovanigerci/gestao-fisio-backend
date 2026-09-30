import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from .models import CodigoVerificacaoEmail
from .serializers import RegistroSerializer, ConfirmarRegistroSerializer, ProfissionalSerializer, PerfilSerializer

logger = logging.getLogger(__name__)


class EnviarCodigoCadastroView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'codigo_email'

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        aguardar = CodigoVerificacaoEmail.segundos_para_reenvio(email)
        if aguardar:
            return Response(
                {'detail': f'Aguarde {aguardar} segundos para pedir um novo código.', 'aguardar_segundos': aguardar},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        codigo = CodigoVerificacaoEmail.gerar(email)
        contexto = {
            'codigo': codigo,
            'validade_minutos': int(CodigoVerificacaoEmail.VALIDADE.total_seconds() // 60),
            'site_url': settings.FRONTEND_URL.rstrip('/'),
        }
        try:
            send_mail(
                subject=f'{codigo} é seu código de verificação — Gestão Fisio',
                message=render_to_string('emails/codigo_verificacao.txt', contexto),
                html_message=render_to_string('emails/codigo_verificacao.html', contexto),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception:
            logger.exception('Falha ao enviar código de verificação de e-mail')
            CodigoVerificacaoEmail.objects.filter(email__iexact=email).delete()
            return Response(
                {'detail': 'Não foi possível enviar o e-mail agora. Tente novamente em instantes.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'detail': 'Enviamos um código de verificação para o seu e-mail.'})


class RegistroView(generics.CreateAPIView):
    serializer_class = ConfirmarRegistroSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registro'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profissional = serializer.save()

        resposta = ProfissionalSerializer(profissional)
        return Response(resposta.data, status=status.HTTP_201_CREATED)


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PerfilSerializer(request.user.profissional, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = PerfilSerializer(request.user.profissional, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
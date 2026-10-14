"""Direitos do titular sobre os próprios dados (LGPD): resumo, exportação e exclusão da conta."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from .exportacao import contar_dados, exportar_dados
from .models import CodigoVerificacaoEmail
from .serializers import ExcluirContaSerializer
from .views_auth import remover_cookies_de_sessao

logger = logging.getLogger(__name__)


class ResumoDosDadosView(APIView):
    """Quantos registros a conta tem: mostrado antes de exportar ou excluir."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(contar_dados(request.user.profissional))


class ExportarDadosView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'exportar_dados'

    def get(self, request):
        nome = f'gestao-fisio-dados-{timezone.localdate():%Y-%m-%d}.zip'
        response = HttpResponse(exportar_dados(request.user.profissional), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{nome}"'
        # Dados de saúde: nenhum cache intermediário ou do navegador guarda o arquivo
        response['Cache-Control'] = 'no-store'
        return response


class ExcluirContaView(APIView):
    """
    Exclusão definitiva e imediata da conta, confirmada pela senha. Apaga o usuário e, em cascata,
    perfil, clínicas, pacientes e sessões; além disso a foto no armazenamento, os tokens de sessão
    e os cookies. A exportação (GET /auth/me/exportar/) é oferecida antes, na mesma tela.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'excluir_conta'  # limita tentativas de senha

    def post(self, request):
        serializer = ExcluirContaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        usuario = request.user
        profissional = usuario.profissional
        email = usuario.email
        nome = usuario.get_full_name() or usuario.username
        foto = profissional.foto.name if profissional.foto else None
        armazenamento = profissional.foto.storage

        with transaction.atomic():
            OutstandingToken.objects.filter(user=usuario).delete()
            if email:
                CodigoVerificacaoEmail.objects.filter(email__iexact=email).delete()
            usuario.delete()
            if foto:
                # Só depois do commit: se a exclusão falhar, a conta continua com a foto dela
                transaction.on_commit(lambda: self._apagar_foto(armazenamento, foto))

        self._avisar_por_email(email, nome)
        return remover_cookies_de_sessao(Response({'detail': 'Conta excluída.'}))

    @staticmethod
    def _apagar_foto(armazenamento, foto):
        try:
            armazenamento.delete(foto)
        except Exception:
            # A conta já foi excluída; um arquivo órfão é melhor que devolver erro ao usuário
            logger.exception('Falha ao apagar a foto de uma conta excluída (%s)', foto)

    @staticmethod
    def _avisar_por_email(email, nome):
        if not email:
            return
        contexto = {'nome': nome, 'site_url': settings.FRONTEND_URL.rstrip('/')}
        try:
            send_mail(
                subject='Sua conta foi excluída — Gestão Fisio',
                message=render_to_string('emails/conta_excluida.txt', contexto),
                html_message=render_to_string('emails/conta_excluida.html', contexto),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception:
            logger.exception('Falha ao enviar o e-mail de conta excluída')

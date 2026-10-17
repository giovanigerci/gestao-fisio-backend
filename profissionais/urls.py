from django.urls import path
from profissionais.views_auth import (
    LogoutView, FotoPerfilView, TrocarSenhaView,
    SolicitarResetSenhaView, RedefinirSenhaView,
)
from .views import ConfirmarTrocaDeEmailView, EnviarCodigoCadastroView, PerfilView, RegistroView, TrocaDeEmailView
from .views_dados import ExcluirContaView, ExportarDadosView, ResumoDosDadosView

urlpatterns = [
    path('registrar/enviar-codigo/', EnviarCodigoCadastroView.as_view(), name='registrar-enviar-codigo'),
    path('registrar/', RegistroView.as_view(), name='registrar'),
    path('me/', PerfilView.as_view(), name='perfil'),
    path('me/email/', TrocaDeEmailView.as_view(), name='perfil-email'),
    path('me/email/confirmar/', ConfirmarTrocaDeEmailView.as_view(), name='perfil-email-confirmar'),
    path('me/foto/', FotoPerfilView.as_view(), name='perfil-foto'),
    path('me/dados/', ResumoDosDadosView.as_view(), name='perfil-dados'),
    path('me/exportar/', ExportarDadosView.as_view(), name='perfil-exportar'),
    path('excluir-conta/', ExcluirContaView.as_view(), name='excluir-conta'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('trocar-senha/', TrocarSenhaView.as_view(), name='trocar-senha'),
    path('esqueci-senha/', SolicitarResetSenhaView.as_view(), name='esqueci-senha'),
    path('redefinir-senha/', RedefinirSenhaView.as_view(), name='redefinir-senha'),
]
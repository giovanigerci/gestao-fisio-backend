from django.urls import path
from profissionais.views_auth import LogoutView, FotoPerfilView
from .views import RegistroView, PerfilView

urlpatterns = [
    path('registrar/', RegistroView.as_view(), name='registrar'),
    path('me/', PerfilView.as_view(), name='perfil'),
    path('me/foto/', FotoPerfilView.as_view(), name='perfil-foto'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
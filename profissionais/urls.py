from django.urls import path
from .views import RegistroView, PerfilView

urlpatterns = [
    path('registrar/', RegistroView.as_view(), name='registrar'),
    path('me/', PerfilView.as_view(), name='perfil'),
]
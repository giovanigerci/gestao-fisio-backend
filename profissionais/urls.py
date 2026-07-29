from django.urls import path
from .views import RegistroView

urlpatterns = [
    path('registrar/', RegistroView.as_view(), name='registrar'),
]
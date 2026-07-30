from django.urls import path
from .views import ResumoFinanceiroView

urlpatterns = [
    path('resumo-financeiro/', ResumoFinanceiroView.as_view(), name='resumo_financeiro'),
]
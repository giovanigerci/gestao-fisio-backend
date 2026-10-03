from django.urls import path
from .views import EvolucaoReceitaView, HistoricoReceitaView, ResumoFinanceiroView

urlpatterns = [
    path('resumo-financeiro/', ResumoFinanceiroView.as_view(), name='resumo_financeiro'),
    path('resumo-financeiro/evolucao/', EvolucaoReceitaView.as_view(), name='evolucao_receita'),
    path('resumo-financeiro/historico/', HistoricoReceitaView.as_view(), name='historico_receita'),
]

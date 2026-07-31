from django.db.models import Count, F, Sum
from django.db.models.functions import TruncWeek, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from agenda.models import Agendamento

class ResumoFinanceiroView(APIView):
    def get(self, request):
        periodo = request.query_params.get('periodo', 'mes')

        if periodo == 'semana':
            trunc_func = TruncWeek('data')
        else: 
            trunc_func = TruncMonth('data')

        agendamentos = Agendamento.objects.filter(
            eh_gratuito=False,
            profissional=request.user.profissional
        )

        resumo = agendamentos.annotate(
            periodo=trunc_func
        ).values(
           'periodo', 'clinica', 'clinica__nome'
        ).annotate(
            total_atendimentos=Count('id'),
            receita_total=F('clinica__valor_por_atendimento') * Count('id'),
        ).order_by('periodo')

        total_geral = sum(item['receita_total'] for item in resumo)

        return Response({
            'por_clinica': resumo,
            'total_geral': total_geral,
        })
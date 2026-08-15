from datetime import date, timedelta
import calendar
from django.db.models import Count, F
from rest_framework.views import APIView
from rest_framework.response import Response
from agenda.models import Agendamento

class ResumoFinanceiroView(APIView):
    def get(self, request):
        periodo = request.query_params.get('periodo', 'mes')
        data_str = request.query_params.get('data')
        
        if data_str:
            hoje = date.fromisoformat(data_str)
        else:
            hoje = date.today()

        if periodo == 'semana':
            inicio = hoje - timedelta(days=hoje.weekday())
            fim = inicio + timedelta(days=6)
        else: 
            inicio = hoje.replace(day=1)
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            fim = hoje.replace(day=ultimo_dia)

        agendamentos = Agendamento.objects.filter(
            eh_experimental=False,
            profissional=request.user.profissional,
            data__gte=inicio,
            data__lte=fim,
        ).exclude(status='CA')

        resumo = agendamentos.values('clinica', 'clinica__nome').annotate(
            total_atendimentos=Count('id'),
            receita_total=F('clinica__valor_por_atendimento') * Count('id'),
        ).order_by('clinica__nome')

        total_geral = sum(item['receita_total'] for item in resumo)

        return Response({
            'por_clinica': resumo,
            'total_geral': total_geral,
        })
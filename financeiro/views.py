from django.db.models import Count, F
from rest_framework.views import APIView
from rest_framework.response import Response
from agenda.models import Agendamento

class ResumoFinanceiroView(APIView):
    def get(self, request):
        agendamentos = Agendamento.objects.filter(
            eh_gratuito=False,
            profissional=request.user.profissional
        )

        resumo = agendamentos.values(
            'clinica', 'clinica__nome'
        ).annotate(
            total_atendimentos=Count('id'),
            receita_total=F('clinica__valor_por_atendimento') * Count('id'),
        )

        return Response(resumo)
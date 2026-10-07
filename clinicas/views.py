from datetime import timedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from agenda.models import Agendamento
from .models import Clinica
from .serializers import ClinicaSerializer

class ClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicaSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome__unaccent']
    ordering_fields = ['nome']
    ordering = ['-ativo', 'nome']

    def get_queryset(self):
        realizado = Q(agendamento__status=Agendamento.Status.REALIZADO)
        inicio_do_mes = timezone.localdate().replace(day=1)
        inicio_do_proximo = (inicio_do_mes + timedelta(days=32)).replace(day=1)
        no_mes = realizado & Q(
            agendamento__eh_experimental=False,
            agendamento__data__gte=inicio_do_mes,
            agendamento__data__lt=inicio_do_proximo,
        )
        return Clinica.objects.filter(
            profissional=self.request.user.profissional
        ).annotate(
            total_atendimentos=Count('agendamento', filter=realizado),
            # Soma do valor congelado (experimental = 0) na mesma consulta da listagem
            receita_total=Sum('agendamento__valor_cobrado', filter=realizado),
            atendimentos_mes=Count('agendamento', filter=no_mes),
            receita_mes=Sum('agendamento__valor_cobrado', filter=no_mes),
        )

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

    @action(detail=False, methods=['get'])
    def opcoes(self, request):
        clinicas = Clinica.objects.filter(profissional=request.user.profissional)
        return Response(list(clinicas.values('id', 'nome', 'cor')))

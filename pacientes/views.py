from datetime import date, timedelta
from django.db.models import Count, Max, Exists, OuterRef, Case, When, Value, CharField, Q
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from agenda.models import Agendamento
from .models import Paciente
from .serializers import PacienteSerializer

class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome__unaccent']
    ordering_fields = ['nome']
    ordering = ['nome']

    def get_queryset(self):
        hoje = date.today()
        limite_recente = hoje - timedelta(days=60)

        recente_subquery = Agendamento.objects.filter(
            paciente=OuterRef('pk'),
            status=Agendamento.Status.REALIZADO,
            data__gte=limite_recente
        )
        futuro_subquery = Agendamento.objects.filter(
            paciente=OuterRef('pk'),
            status=Agendamento.Status.AGENDADO,
            data__gte=hoje
        )

        return Paciente.objects.filter(
            profissional=self.request.user.profissional
        ).annotate(
            total_sessoes=Count('agendamento', filter=Q(agendamento__status=Agendamento.Status.REALIZADO)),
            ultima_visita=Max('agendamento__data', filter=Q(agendamento__status=Agendamento.Status.REALIZADO)),
            status=Case(
                When(Exists(recente_subquery), then=Value('Ativo')),
                When(Exists(futuro_subquery), then=Value('Ativo')),
                default=Value('Inativo'),
                output_field=CharField()
            )
        )

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

    @action(detail=False, methods=['get'])
    def opcoes(self, request):
        pacientes = Paciente.objects.filter(profissional=request.user.profissional)
        return Response(list(pacientes.values('id', 'nome')))
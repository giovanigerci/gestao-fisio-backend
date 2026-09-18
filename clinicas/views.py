from django.db.models import Count, Q
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
    ordering = ['nome']

    def get_queryset(self):
        return Clinica.objects.filter(
            profissional=self.request.user.profissional
        ).annotate(
            total_atendimentos=Count('agendamento', filter=Q(agendamento__status=Agendamento.Status.REALIZADO))
        )

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

    @action(detail=False, methods=['get'])
    def opcoes(self, request):
        clinicas = Clinica.objects.filter(profissional=request.user.profissional)
        return Response(list(clinicas.values('id', 'nome')))

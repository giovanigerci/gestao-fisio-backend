from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Paciente
from .serializers import PacienteSerializer

class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome']
    ordering_fields = ['nome']
    ordering = ['nome']

    def get_queryset(self):
        return Paciente.objects.filter(profissional=self.request.user.profissional)

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

    @action(detail=False, methods=['get'])
    def opcoes(self, request):
        pacientes = self.get_queryset()
        dados = [{'id': paciente.id, 'nome': paciente.nome} for paciente in pacientes]
        return Response(dados)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Clinica
from .serializers import ClinicaSerializer

class ClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicaSerializer

    def get_queryset(self):
        return Clinica.objects.filter(profissional=self.request.user.profissional)

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

    @action(detail=False, methods=['get'])
    def opcoes(self, request):
        clinicas = self.get_queryset()
        dados = [{'id': clinica.id, 'nome': clinica.nome} for clinica in clinicas]
        return Response(dados)

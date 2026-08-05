from rest_framework import viewsets
from .models import Clinica
from .serializers import ClinicaSerializer

class ClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicaSerializer

    def get_queryset(self):
        return Clinica.objects.filter(profissional=self.request.user.profissional)

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)

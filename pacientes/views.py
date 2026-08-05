from rest_framework import viewsets
from .models import Paciente
from .serializers import PacienteSerializer

class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    
    def get_queryset(self):
        return Paciente.objects.filter(profissional=self.request.user.profissional)

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)
    
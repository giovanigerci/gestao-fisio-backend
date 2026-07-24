from rest_framework import viewsets
from .models import Clinica, VinculoClinica
from .serializers import ClinicaSerializer, VinculoClinicaSerializer

class ClinicaViewSet(viewsets.ModelViewSet):
    queryset = Clinica.objects.all()
    serializer_class = ClinicaSerializer

class VinculoClinicaViewSet(viewsets.ModelViewSet):
    queryset = VinculoClinica.objects.all()
    serializer_class = VinculoClinicaSerializer

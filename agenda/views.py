from rest_framework import viewsets
from .models import Agendamento
from .serializers import AgendamentoSerializer

class AgendamentoViewSet(viewsets.ModelViewSet):
    queryset = Agendamento.objects.all()
    serializer_class = AgendamentoSerializer
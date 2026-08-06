from rest_framework import viewsets
from .models import Agendamento
from .serializers import AgendamentoSerializer

class AgendamentoViewSet(viewsets.ModelViewSet):
    serializer_class = AgendamentoSerializer

    def get_queryset(self):
        queryset = Agendamento.objects.filter(profissional=self.request.user.profissional)

        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')

        if data_inicio and data_fim:
            queryset = queryset.filter(data__gte=data_inicio, data__lte=data_fim)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(profissional=self.request.user.profissional)
    
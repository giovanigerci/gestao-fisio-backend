import uuid
from datetime import timedelta
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.validators import UniqueTogetherValidator
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

    def list(self, request, *args, **kwargs):
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')

        if data_inicio and data_fim:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def recorrente(self, request):
        try:
            repeticoes = int(request.data.get('repeticoes', 0))
        except (ValueError, TypeError):
            return Response({'repeticoes': 'Deve ser um número inteiro.'}, status=400)

        if not (1 <= repeticoes <=12):
            return Response({'repeticoes': 'Informe um número entre 1 e 12.'}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.validators = [
            v for v in serializer.validators if not isinstance(v, UniqueTogetherValidator)
        ]
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        grupo = uuid.uuid4()
        agendamentos_criados = []
        agendamentos_conflitantes = []

        for i in range(repeticoes):
            data_ocorrencia = dados['data'] + timedelta(weeks=i)
            try:
                agendamento = Agendamento.objects.create(
                    profissional = request.user.profissional,
                    clinica = dados['clinica'],
                    paciente = dados['paciente'],
                    data = data_ocorrencia,
                    hora_inicio = dados['hora_inicio'],
                    hora_fim = dados['hora_fim'],
                    eh_experimental = dados.get('eh_experimental', False),
                    grupo_recorrencia = grupo,
                )
                agendamentos_criados.append(AgendamentoSerializer(agendamento).data)
            except IntegrityError:
                agendamentos_conflitantes.append(str(data_ocorrencia))
            
        return Response({
            'agendamentos_criados': agendamentos_criados,
            'agendamentos_conflitantes': agendamentos_conflitantes},
            status=status.HTTP_201_CREATED)
                    
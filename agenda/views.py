import uuid
from datetime import datetime, timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.validators import UniqueTogetherValidator
from .models import Agendamento
from .serializers import AgendamentoSerializer

class AgendamentoViewSet(viewsets.ModelViewSet):
    serializer_class = AgendamentoSerializer

    def get_queryset(self):
        queryset = Agendamento.objects.filter(
            profissional=self.request.user.profissional
        ).select_related('paciente', 'clinica')

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

    @action(detail=False, methods=['patch'], url_path='confirmar-dia')
    def confirmar_dia(self, request):
        data_str = request.query_params.get('data') or request.data.get('data')
        if not data_str:
            return Response({'erro': 'O parâmetro "data" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data_alvo = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'erro': 'Formato de data inválido. Utilize YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        hoje = timezone.localdate()
        if data_alvo > hoje:
            return Response({'erro': 'Não é possível confirmar atendimentos de uma data futura.'}, status=status.HTTP_400_BAD_REQUEST)

        profissional = request.user.profissional
        agendamentos_dia = Agendamento.objects.filter(
            profissional=profissional,
            data=data_alvo
        )

        if not agendamentos_dia.exists():
            return Response({'erro': 'Não há agendamentos cadastrados para este dia.'}, status=status.HTTP_400_BAD_REQUEST)

        if data_alvo == hoje:
            ultimo_agendamento = agendamentos_dia.order_by('-hora_fim').first()
            if ultimo_agendamento:
                hora_atual = timezone.localtime().time()
                if hora_atual < ultimo_agendamento.hora_fim:
                    return Response(
                        {'erro': 'O expediente de hoje ainda não foi encerrado. Aguarde o término do último atendimento.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        pendentes = agendamentos_dia.filter(status=Agendamento.Status.AGENDADO)
        total_pendentes = pendentes.count()
        if total_pendentes == 0:
            return Response(
                {'erro': 'Não há agendamentos pendentes para confirmar neste dia.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            pendentes.update(status=Agendamento.Status.REALIZADO)

        agendamentos_atualizados = Agendamento.objects.filter(
            profissional=profissional,
            data=data_alvo
        ).select_related('paciente', 'clinica').order_by('hora_inicio')

        serializer = self.get_serializer(agendamentos_atualizados, many=True)
        return Response({
            'mensagem': f'{total_pendentes} atendimento(s) confirmado(s) com sucesso.',
            'total_confirmados': total_pendentes,
            'agendamentos': serializer.data
        }, status=status.HTTP_200_OK)
                    
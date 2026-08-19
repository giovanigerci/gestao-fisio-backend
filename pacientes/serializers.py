from rest_framework import serializers
from agenda.models import Agendamento
from datetime import date, timedelta
from .models import Paciente

class PacienteSerializer(serializers.ModelSerializer):
    ultima_visita = serializers.SerializerMethodField()
    total_sessoes = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    
    class Meta:
        model = Paciente
        fields = ['id', 'profissional', 'nome', 'cpf', 'telefone', 'email', 'data_nascimento', 'endereco', 'historico_medico',
                  'ultima_visita', 'total_sessoes', 'status']
        read_only_fields = ['profissional']

    def get_total_sessoes(self, obj):
        return Agendamento.objects.filter(paciente=obj, status='RE').count()

    def get_ultima_visita(self, obj):
        ultimo = Agendamento.objects.filter(paciente=obj, status='RE').order_by('-data').first()
        return ultimo.data if ultimo else None

    def get_status(self, obj):
        limite = date.today() - timedelta(days=60)
        tem_recente = Agendamento.objects.filter(paciente=obj, status='RE', data__gte=limite).exists()
        tem_futuro = Agendamento.objects.filter(paciente=obj, status='AG', data__gte=date.today()).exists()
        return 'Ativo' if (tem_recente or tem_futuro) else 'Inativo'
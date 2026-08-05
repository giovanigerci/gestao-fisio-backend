from rest_framework import serializers
from .models import Agendamento

class AgendamentoSerializer(serializers.ModelSerializer):
    valor_calculado = serializers.SerializerMethodField()

    class Meta:
        model = Agendamento
        fields = ['id', 'profissional', 'clinica', 'paciente', 'data', 'hora_inicio',
                   'hora_fim', 'status', 'eh_experimental', 'eh_gratuito', 'valor_calculado']
        read_only_fields = ['profissional']

    def get_valor_calculado(self, obj):
        if obj.eh_gratuito:
            return 0
        return obj.clinica.valor_por_atendimento

from rest_framework import serializers
from .models import Clinica
from agenda.models import Agendamento

class ClinicaSerializer(serializers.ModelSerializer):
    total_atendimentos = serializers.SerializerMethodField()
    receita_total = serializers.SerializerMethodField()

    class Meta:
        model = Clinica
        fields = ['id', 'profissional', 'nome', 'endereco', 'telefone',
                  'valor_por_atendimento', 'ativo', 'total_atendimentos', 'receita_total']
        read_only_fields = ['profissional']

    def get_total_atendimentos(self, obj):
        return Agendamento.objects.filter(clinica=obj, status='RE').count()

    def get_receita_total(self, obj):
        total = self.get_total_atendimentos(obj)
        return obj.valor_por_atendimento * total

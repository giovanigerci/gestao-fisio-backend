from django.db.models import Sum
from rest_framework import serializers
from .models import Clinica
from agenda.models import Agendamento

class ClinicaSerializer(serializers.ModelSerializer):
    total_atendimentos = serializers.SerializerMethodField()
    receita_total = serializers.SerializerMethodField()
    atendimentos_mes = serializers.SerializerMethodField()
    receita_mes = serializers.SerializerMethodField()

    class Meta:
        model = Clinica
        fields = ['id', 'profissional', 'nome', 'endereco', 'telefone',
                  'valor_por_atendimento', 'ativo', 'cor', 'total_atendimentos', 'receita_total',
                  'atendimentos_mes', 'receita_mes']
        read_only_fields = ['profissional', 'cor']

    def validate_valor_por_atendimento(self, value):
        if value < 0:
            raise serializers.ValidationError('O valor não pode ser negativo.')
        return value

    def get_total_atendimentos(self, obj):
        if hasattr(obj, 'total_atendimentos'):
            return obj.total_atendimentos
        return Agendamento.objects.filter(clinica=obj, status='RE').count()

    def get_receita_total(self, obj):
        if hasattr(obj, 'receita_total'):
            return obj.receita_total or 0
        return Agendamento.objects.filter(clinica=obj, status='RE').aggregate(total=Sum('valor_cobrado'))['total'] or 0

    def get_atendimentos_mes(self, obj):
        return getattr(obj, 'atendimentos_mes', 0)

    def get_receita_mes(self, obj):
        return getattr(obj, 'receita_mes', None) or 0

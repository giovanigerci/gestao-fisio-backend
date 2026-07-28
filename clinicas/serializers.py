from rest_framework import serializers
from .models import Clinica

class ClinicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = ['id', 'profissional', 'nome', 'endereco', 'telefone', 'valor_por_atendimento', 'ativo']

from rest_framework import serializers
from .models import Paciente

class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ['id', 'profissional', 'nome', 'cpf', 'telefone', 'email', 'data_nascimento', 'endereco', 'historico_medico']
        read_only_fields = ['profissional']
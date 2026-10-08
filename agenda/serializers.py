from django.utils import timezone
from rest_framework import serializers
from pacientes.models import Paciente
from .models import Agendamento

class AgendamentoSerializer(serializers.ModelSerializer):
    valor_calculado = serializers.SerializerMethodField()
    nome_paciente = serializers.CharField(source='paciente.nome', read_only=True)
    nome_clinica = serializers.CharField(source='clinica.nome', read_only=True)
    cor_clinica = serializers.IntegerField(source='clinica.cor', read_only=True)
    idade_paciente = serializers.SerializerMethodField()

    class Meta:
        model = Agendamento
        fields = ['id', 'profissional', 'clinica', 'paciente', 'data', 'hora_inicio',
                   'hora_fim', 'status', 'eh_experimental', 'valor_calculado',
                   'nome_paciente', 'nome_clinica', 'cor_clinica', 'idade_paciente']
        read_only_fields = ['profissional']

    def get_idade_paciente(self, obj):
        if obj.paciente and obj.paciente.data_nascimento:
            hoje = timezone.localdate()
            nasc = obj.paciente.data_nascimento
            idade = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
            return f"{idade} Anos"
        return ""

    def get_valor_calculado(self, obj):
        if obj.valor_cobrado is not None:
            return obj.valor_cobrado
        if obj.eh_experimental:
            return 0
        return obj.clinica.valor_por_atendimento

    def validate(self, dados):
        profissional = self.context['request'].user.profissional

        clinica = dados.get('clinica')
        if clinica and clinica.profissional != profissional:
            raise serializers.ValidationError("Você não pode agendar em uma clínica que não pertence a você.")

        paciente = dados.get('paciente')
        if paciente and paciente.profissional != profissional:
            raise serializers.ValidationError("Você não pode agendar um paciente que não pertence a você.")

        return dados


class VerificarRecorrenciaSerializer(serializers.Serializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.none())
    data = serializers.DateField()
    hora_inicio = serializers.TimeField()
    repeticoes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = Paciente.objects.filter(profissional=self.context['request'].user.profissional)

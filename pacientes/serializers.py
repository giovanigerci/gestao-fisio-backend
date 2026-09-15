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
        extra_kwargs = {
            'cpf': {
                'error_messages': {
                    'unique': 'Já existe um paciente cadastrado com este CPF.'
                }
            },
            'email': {
                'error_messages': {
                    'unique': 'Já existe um paciente cadastrado com este e-mail.'
                }
            }
        }

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

    def validate_data_nascimento(self, value):
        if value:
            if value > date.today():
                raise serializers.ValidationError("Data de nascimento não pode ser maior que a data atual.")
            limite_antigo = date.today().replace(year=date.today().year - 120)
            if value < limite_antigo:
                raise serializers.ValidationError("Data de nascimento inválida.")
        return value
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from .models import Profissional

class ProfissionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profissional
        fields = ['id', 'usuario', 'telefone', 'especialidade', 'crefito']

class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    telefone = serializers.CharField(max_length=20)
    especialidade = serializers.CharField(max_length=100)
    crefito = serializers.CharField(max_length=15)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def validate_crefito(self, value):
        if Profissional.objects.filter(crefito=value).exists():
            raise serializers.ValidationError("Este CREFITO já está em uso.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            usuario = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password']
            )
            profissional = Profissional.objects.create(
                usuario=usuario,
                telefone=validated_data['telefone'],
                especialidade=validated_data['especialidade'],
                crefito=validated_data['crefito']
            )
        return profissional
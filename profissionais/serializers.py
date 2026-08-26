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

class PerfilSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    telefone = serializers.CharField(max_length=20, required=False)
    especialidade = serializers.CharField(max_length=100, required=False)
    crefito = serializers.CharField(max_length=15, required=False)

    def validate_crefito(self, value):
        query = Profissional.objects.filter(crefito=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError('Este CREFITO já está em uso por outro profissional.')
        return value

    def update(self, instance, validated_data):
        usuario = instance.usuario
        for campo in ('first_name', 'last_name', 'email'):
            if campo in validated_data:
                setattr(usuario, campo, validated_data[campo])
        usuario.save()

        for campo in ('telefone', 'especialidade', 'crefito'):
            if campo in validated_data:
                setattr(instance, campo, validated_data[campo])
        instance.save()

        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        foto_url = request.build_absolute_uri(instance.foto.url) if instance.foto and request else None
        return {
            'id': instance.id,
            'username': instance.usuario.username,
            'first_name': instance.usuario.first_name,
            'last_name': instance.usuario.last_name,
            'email': instance.usuario.email,
            'telefone': instance.telefone,
            'especialidade': instance.especialidade,
            'crefito': instance.crefito,
            'foto': foto_url,
        }

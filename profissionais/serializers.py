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

class FotoPerfilSerializer(serializers.Serializer):
    TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5 MB
    FORMATOS_PERMITIDOS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}

    foto = serializers.ImageField(error_messages={
        'required': 'Nenhum arquivo enviado.',
        'empty': 'O arquivo enviado está vazio.',
        'invalid_image': 'O arquivo enviado não é uma imagem válida.',
    })

    def validate_foto(self, value):
        if value.size > self.TAMANHO_MAXIMO:
            raise serializers.ValidationError('A imagem deve ter no máximo 5 MB.')

        formato = getattr(getattr(value, 'image', None), 'format', None)
        if formato not in self.FORMATOS_PERMITIDOS:
            raise serializers.ValidationError('Formato não suportado. Envie uma imagem JPEG, PNG ou WEBP.')

        value.name = f'foto{self.FORMATOS_PERMITIDOS[formato]}'
        return value

class TrocarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(write_only=True)
    confirmar_senha = serializers.CharField(write_only=True)

    def validate_senha_atual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Senha atual incorreta.')
        return value

    def validate(self, data):
        if data['nova_senha'] != data['confirmar_senha']:
            raise serializers.ValidationError({'confirmar_senha': 'As senhas não coincidem.'})

        # Aplica os validadores de senha do Django (mínimo 8 chars, etc.)
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(data['nova_senha'], self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({'nova_senha': list(e.messages)})

        return data

class RedefinirSenhaSerializer(serializers.Serializer):
    nova_senha = serializers.CharField(write_only=True)
    confirmar_senha = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['nova_senha'] != data['confirmar_senha']:
            raise serializers.ValidationError({'confirmar_senha': 'As senhas não coincidem.'})

        from django.contrib.auth.password_validation import validate_password
        user = self.context.get('user')
        try:
            validate_password(data['nova_senha'], user)
        except Exception as e:
            raise serializers.ValidationError({'nova_senha': list(e.messages)})

        return data

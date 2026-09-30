from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from .models import CodigoVerificacaoEmail, Profissional

# Mensagem única com todos os requisitos (em vez de uma linha por validador que falhou).
# Mantenha em sincronia com AUTH_PASSWORD_VALIDATORS e com o componente de requisitos no frontend.
MENSAGEM_SENHA_FRACA = (
    'A senha deve ter pelo menos 8 caracteres, com letras e números, '
    'e não pode ser uma senha comum nem parecida com seu nome de usuário.'
)


def validar_senha(senha, usuario, campo):
    """Aplica AUTH_PASSWORD_VALIDATORS e devolve a mensagem única de requisitos no campo indicado."""
    try:
        validate_password(senha, usuario)
    except DjangoValidationError:
        raise serializers.ValidationError({campo: [MENSAGEM_SENHA_FRACA]})


class ProfissionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profissional
        fields = ['id', 'usuario', 'telefone', 'especialidade', 'crefito']


def validar_email_unico(email, excluir_usuario=None):
    query = User.objects.filter(email__iexact=email)
    if excluir_usuario is not None:
        query = query.exclude(pk=excluir_usuario.pk)
    if query.exists():
        raise serializers.ValidationError('Este e-mail já está em uso.')


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    telefone = serializers.CharField(max_length=20)
    especialidade = serializers.CharField(max_length=100)
    crefito = serializers.CharField(max_length=15)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        validar_email_unico(value)
        return value

    def validate_crefito(self, value):
        if Profissional.objects.filter(crefito=value).exists():
            raise serializers.ValidationError("Este CREFITO já está em uso.")
        return value

    def validate(self, data):
        validar_senha(data['password'], User(username=data['username'], email=data['email']), 'password')
        return data


class ConfirmarRegistroSerializer(RegistroSerializer):
    codigo = serializers.RegexField(r'^\d{6}$', write_only=True, error_messages={
        'invalid': 'O código deve ter 6 dígitos.',
    })

    def validate(self, data):
        data = super().validate(data)
        if not CodigoVerificacaoEmail.verificar(data['email'], data['codigo']):
            raise serializers.ValidationError({'codigo': 'Código inválido ou expirado.'})
        return data

    def create(self, validated_data):
        with transaction.atomic():
            usuario = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password']
            )
            profissional = Profissional.objects.create(
                usuario=usuario,
                telefone=validated_data['telefone'],
                especialidade=validated_data['especialidade'],
                crefito=validated_data['crefito']
            )
            CodigoVerificacaoEmail.objects.filter(email__iexact=validated_data['email']).delete()
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

    def validate_email(self, value):
        value = value.strip().lower()
        if value:
            validar_email_unico(value, excluir_usuario=self.instance.usuario if self.instance else None)
        return value

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

        validar_senha(data['nova_senha'], self.context['request'].user, 'nova_senha')
        return data

class RedefinirSenhaSerializer(serializers.Serializer):
    nova_senha = serializers.CharField(write_only=True)
    confirmar_senha = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['nova_senha'] != data['confirmar_senha']:
            raise serializers.ValidationError({'confirmar_senha': 'As senhas não coincidem.'})

        validar_senha(data['nova_senha'], self.context.get('user'), 'nova_senha')
        return data

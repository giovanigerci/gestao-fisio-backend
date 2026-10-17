import math
import secrets
import uuid
from datetime import timedelta
from pathlib import Path
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac


def caminho_foto_perfil(instance, filename):
    extensao = Path(filename).suffix.lower()
    return f'perfis/{uuid.uuid4().hex}{extensao}'


class Profissional(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    especialidade = models.CharField(max_length=100)
    crefito = models.CharField(max_length=15, unique=True)
    foto = models.ImageField(upload_to=caminho_foto_perfil, null=True, blank=True)

    class Meta:
        verbose_name = 'Profissional'
        verbose_name_plural = 'Profissionais'

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username


class CodigoVerificacaoEmail(models.Model):
    VALIDADE = timedelta(minutes=10)
    MAX_TENTATIVAS = 5
    INTERVALO_REENVIO = timedelta(seconds=60)
    CADASTRO = 'cadastro'

    email = models.EmailField(db_index=True)
    finalidade = models.CharField(max_length=40, default=CADASTRO)
    codigo_hash = models.CharField(max_length=64)
    tentativas = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Código de verificação de e-mail'
        verbose_name_plural = 'Códigos de verificação de e-mail'

    @staticmethod
    def troca_de_email(usuario):
        """Finalidade do código que confirma o novo e-mail: só vale para este usuário."""
        return f'troca_email:{usuario.pk}'

    @staticmethod
    def _hash(email, codigo):
        return salted_hmac('profissionais.CodigoVerificacaoEmail', f'{email.lower()}:{codigo}').hexdigest()

    @classmethod
    def _do_email(cls, email, finalidade):
        return cls.objects.filter(email__iexact=email, finalidade=finalidade)

    @classmethod
    def gerar(cls, email, finalidade=CADASTRO):
        codigo = f'{secrets.randbelow(10**6):06d}'
        cls._do_email(email, finalidade).delete()
        cls.objects.create(email=email.lower(), finalidade=finalidade, codigo_hash=cls._hash(email, codigo))
        return codigo

    @classmethod
    def segundos_para_reenvio(cls, email, finalidade=CADASTRO):
        ultimo = cls._do_email(email, finalidade).order_by('-criado_em').first()
        if not ultimo:
            return 0
        restante = ultimo.criado_em + cls.INTERVALO_REENVIO - timezone.now()
        return max(0, math.ceil(restante.total_seconds()))

    @classmethod
    def verificar(cls, email, codigo, finalidade=CADASTRO):
        registro = cls._do_email(email, finalidade).order_by('-criado_em').first()
        if not registro or registro.expirado or registro.tentativas >= cls.MAX_TENTATIVAS:
            return False

        if constant_time_compare(registro.codigo_hash, cls._hash(email, codigo)):
            return True

        registro.tentativas = models.F('tentativas') + 1
        registro.save(update_fields=['tentativas'])
        return False

    @property
    def expirado(self):
        return timezone.now() > self.criado_em + self.VALIDADE

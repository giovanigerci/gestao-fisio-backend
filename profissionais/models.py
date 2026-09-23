import uuid
from pathlib import Path
from django.db import models
from django.contrib.auth.models import User


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
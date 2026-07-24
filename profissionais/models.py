from django.db import models
from django.contrib.auth.models import User

class Profissional(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    especialidade = models.CharField(max_length=100)
    crefito = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = 'Profissional'
        verbose_name_plural = 'Profissionais'

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username
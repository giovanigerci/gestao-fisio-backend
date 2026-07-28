from django.db import models
from profissionais.models import Profissional

class Clinica(models.Model):
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    endereco = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True)
    valor_por_atendimento = models.DecimalField(max_digits=6, decimal_places=2)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
    
from django.db import models
from profissionais.models import Profissional

class Paciente(models.Model):
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    endereco = models.TextField(blank=True)
    historico_medico = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['profissional', 'cpf'], name='unique_profissional_cpf'),
            models.UniqueConstraint(fields=['profissional', 'email'], name='unique_profissional_email'),
        ]

    def __str__(self):
        return self.nome

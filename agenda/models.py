from django.db import models
from django.db.models import Q
from clinicas.models import Clinica
from pacientes.models import Paciente
from profissionais.models import Profissional

class Agendamento(models.Model):
    class Status(models.TextChoices):
        AGENDADO = 'AG', 'Agendado'
        REALIZADO = 'RE', 'Realizado'
        CANCELADO = 'CA', 'Cancelado'

    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.AGENDADO)
    eh_experimental = models.BooleanField(default=False)
    grupo_recorrencia = models.UUIDField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['paciente', 'data', 'hora_inicio'],
                condition=~Q(status='CA'),
                name='paciente_sem_conflito_agendamento',
            )
        ]

    def __str__(self):
        return f"{self.paciente} - {self.data} {self.hora_inicio}"
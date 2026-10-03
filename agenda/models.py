from decimal import Decimal
from django.db import models
from django.db.models import Case, OuterRef, Q, Subquery, Value, When
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
    valor_cobrado = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    _CAMPOS_DO_VALOR = ('status', 'clinica_id', 'eh_experimental')

    class Meta:
        indexes = [
            models.Index(fields=['data'], name='agenda_agendamento_data_idx'),
            models.Index(fields=['profissional', 'status', 'data'], name='agenda_prof_status_data_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['paciente', 'data', 'hora_inicio'],
                condition=~Q(status='CA'),
                name='paciente_sem_conflito_agendamento',
            )
        ]

    def __str__(self):
        return f"{self.paciente} - {self.data} {self.hora_inicio}"

    @classmethod
    def from_db(cls, db, field_names, values):
        instancia = super().from_db(db, field_names, values)
        instancia._estado_original = instancia._estado_do_valor()
        return instancia

    def _estado_do_valor(self):
        return tuple(self.__dict__.get(campo) for campo in self._CAMPOS_DO_VALOR)

    def save(self, *args, **kwargs):
        self._atualizar_valor_cobrado()
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = {*kwargs['update_fields'], 'valor_cobrado'}
        super().save(*args, **kwargs)
        self._estado_original = self._estado_do_valor()

    def _atualizar_valor_cobrado(self):
        if self.status != self.Status.REALIZADO:
            self.valor_cobrado = None
            return

        mudou = getattr(self, '_estado_original', None) != self._estado_do_valor()
        if self.valor_cobrado is None or mudou:
            self.valor_cobrado = Decimal('0.00') if self.eh_experimental else self.clinica.valor_por_atendimento

    @staticmethod
    def expressao_valor_a_cobrar():
        preco_da_clinica = Clinica.objects.filter(pk=OuterRef('clinica_id')).values('valor_por_atendimento')[:1]
        return Case(
            When(eh_experimental=True, then=Value(Decimal('0.00'))),
            default=Subquery(preco_da_clinica),
            output_field=models.DecimalField(max_digits=6, decimal_places=2),
        )

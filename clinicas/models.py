from collections import Counter

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from profissionais.models import Profissional

QUANTIDADE_DE_CORES = 5


def escolher_cor(cores_em_uso):
    contagem = Counter(cores_em_uso)
    return min(range(1, QUANTIDADE_DE_CORES + 1), key=lambda cor: (contagem[cor], cor))


class Clinica(models.Model):
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    endereco = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True)
    valor_por_atendimento = models.DecimalField(max_digits=6, decimal_places=2)
    ativo = models.BooleanField(default=True)
    cor = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(QUANTIDADE_DE_CORES)],
    )

    def save(self, *args, **kwargs):
        if self.cor is None:
            em_uso = Clinica.objects.filter(profissional_id=self.profissional_id).values_list('cor', flat=True)
            self.cor = escolher_cor(em_uso)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

from collections import Counter, defaultdict

import django.core.validators
from django.db import migrations, models

QUANTIDADE_DE_CORES = 5


def atribuir_cores(apps, schema_editor):
    Clinica = apps.get_model('clinicas', 'Clinica')
    clinicas = list(Clinica.objects.order_by('profissional_id', 'id'))
    em_uso = defaultdict(Counter)

    for clinica in clinicas:
        usadas = em_uso[clinica.profissional_id]
        atual = clinica.id % QUANTIDADE_DE_CORES + 1
        if usadas[atual]:
            atual = min(range(1, QUANTIDADE_DE_CORES + 1), key=lambda cor: (usadas[cor], cor))
        clinica.cor = atual
        usadas[atual] += 1

    Clinica.objects.bulk_update(clinicas, ['cor'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('clinicas', '0002_clinica_ativo_clinica_profissional_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinica',
            name='cor',
            field=models.PositiveSmallIntegerField(
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
        migrations.RunPython(atribuir_cores, migrations.RunPython.noop),
    ]

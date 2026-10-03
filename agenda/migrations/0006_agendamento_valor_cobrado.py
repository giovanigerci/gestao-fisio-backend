from decimal import Decimal

from django.db import migrations, models
from django.db.models import Case, OuterRef, Subquery, Value, When


def congelar_valor_dos_realizados(apps, schema_editor):
    Agendamento = apps.get_model('agenda', 'Agendamento')
    Clinica = apps.get_model('clinicas', 'Clinica')
    preco_da_clinica = Clinica.objects.filter(pk=OuterRef('clinica_id')).values('valor_por_atendimento')[:1]

    Agendamento.objects.filter(status='RE').update(
        valor_cobrado=Case(
            When(eh_experimental=True, then=Value(Decimal('0.00'))),
            default=Subquery(preco_da_clinica),
            output_field=models.DecimalField(max_digits=6, decimal_places=2),
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0005_agendamento_agenda_agendamento_data_idx'),
        ('clinicas', '0002_clinica_ativo_clinica_profissional_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamento',
            name='valor_cobrado',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.RunPython(congelar_valor_dos_realizados, migrations.RunPython.noop),
    ]

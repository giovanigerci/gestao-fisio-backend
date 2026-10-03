from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('agenda', '0006_agendamento_valor_cobrado'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='agendamento',
            index=models.Index(fields=['profissional', 'status', 'data'], name='agenda_prof_status_data_idx'),
        ),
    ]

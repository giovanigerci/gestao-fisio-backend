import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('clinicas', '0003_clinica_cor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clinica',
            name='cor',
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
    ]

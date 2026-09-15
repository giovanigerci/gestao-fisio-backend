from django.apps import AppConfig


class PacientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pacientes'

    def ready(self):
        from django.db.models import CharField, TextField
        from django.contrib.postgres.lookups import Unaccent

        CharField.register_lookup(Unaccent)
        TextField.register_lookup(Unaccent)


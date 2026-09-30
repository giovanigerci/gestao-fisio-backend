import re
from django.core.exceptions import ValidationError


class LetrasENumerosValidator:
    """Exige ao menos uma letra e um número (substitui o NumericPasswordValidator do Django)."""

    def validate(self, password, user=None):
        if not (re.search(r'[^\W\d_]', password) and re.search(r'\d', password)):
            raise ValidationError('A senha deve conter letras e números.', code='password_sem_letras_e_numeros')

    def get_help_text(self):
        return 'Sua senha deve conter letras e números.'

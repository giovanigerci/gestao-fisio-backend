import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginPorContaThrottle(SimpleRateThrottle):
    """Limita as tentativas de login por nome de usuário, mesmo vindas de IPs diferentes."""

    scope = 'login_conta'

    def get_cache_key(self, request, view):
        dados = request.data if hasattr(request.data, 'get') else {}
        usuario = str(dados.get('username', '')).strip().lower()
        if not usuario:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': hashlib.sha256(usuario.encode()).hexdigest()}

from urllib.parse import urlsplit

from django.conf import settings
from django.http import JsonResponse

METODOS_SEGUROS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}


class VerificarOrigemMiddleware:
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origem = request.META.get('HTTP_ORIGIN')
        if request.method not in METODOS_SEGUROS and origem and not self._permitida(origem, request):
            return JsonResponse({'detail': 'Origem não permitida.'}, status=403)
        return self.get_response(request)

    @staticmethod
    def _permitida(origem, request):
        return origem in settings.CORS_ALLOWED_ORIGINS or urlsplit(origem).netloc == request.get_host()

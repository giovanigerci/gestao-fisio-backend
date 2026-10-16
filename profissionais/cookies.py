from django.conf import settings

COOKIE_ACCESS = ('access', '/api/')
COOKIE_REFRESH = ('refresh', '/api/auth/')
DURACAO_ACCESS = 5 * 60
DURACAO_REFRESH = 24 * 60 * 60
DURACAO_REFRESH_LONGA = 30 * 24 * 60 * 60

COOKIES_ANTIGOS = (('access_token', '/api/'), ('refresh_token', '/api/auth/token/refresh/'))


def ler_access(request):
    return request.COOKIES.get(COOKIE_ACCESS[0]) or request.COOKIES.get(COOKIES_ANTIGOS[0][0])


def ler_refresh(request):
    return request.COOKIES.get(COOKIE_REFRESH[0]) or request.COOKIES.get(COOKIES_ANTIGOS[1][0])


def _apagar_cookie(response, nome, caminho, dominio=None):
    response.delete_cookie(nome, path=caminho, domain=dominio, samesite=settings.COOKIE_SAMESITE)
    response.cookies[nome]['secure'] = settings.COOKIE_SECURE


def _apagar_cookies_antigos(response):
    for nome, caminho in COOKIES_ANTIGOS:
        _apagar_cookie(response, nome, caminho, settings.COOKIE_DOMAIN)


def definir_cookies_de_sessao(response, refresh, sessao_longa):
    valores = (
        (COOKIE_ACCESS, str(refresh.access_token), DURACAO_ACCESS),
        (COOKIE_REFRESH, str(refresh), DURACAO_REFRESH_LONGA if sessao_longa else DURACAO_REFRESH),
    )
    for (nome, caminho), valor, duracao in valores:
        response.set_cookie(
            nome, valor, max_age=duracao, path=caminho, httponly=True,
            secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        )
    _apagar_cookies_antigos(response)
    return response


def remover_cookies_de_sessao(response):
    for nome, caminho in (COOKIE_ACCESS, COOKIE_REFRESH):
        _apagar_cookie(response, nome, caminho)
    _apagar_cookies_antigos(response)
    return response

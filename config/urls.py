from django.contrib import admin
from django.urls import path, include
from profissionais.views_auth import LoginCookieView, RefreshCookieView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('agenda.urls')),
    path('api/', include('clinicas.urls')),
    path('api/', include('pacientes.urls')),
    path('api/', include('financeiro.urls')),
    path('api/auth/', include('profissionais.urls')),
    path('api/auth/token/', LoginCookieView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', RefreshCookieView.as_view(), name='token_refresh'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
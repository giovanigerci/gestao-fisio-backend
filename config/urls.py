from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('agenda.urls')),
    path('api/', include('clinicas.urls')),
    path('api/', include('pacientes.urls')),
]

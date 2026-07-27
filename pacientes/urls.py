from rest_framework.routers import DefaultRouter
from .views import PacienteViewSet

router = DefaultRouter()
router.register('pacientes', PacienteViewSet, basename='paciente')

urlpatterns = router.urls
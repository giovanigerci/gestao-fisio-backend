from rest_framework.routers import DefaultRouter
from .views import ClinicaViewSet

router = DefaultRouter()
router.register('clinicas', ClinicaViewSet, basename='clinica')

urlpatterns = router.urls
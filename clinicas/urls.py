from rest_framework.routers import DefaultRouter
from .views import ClinicaViewSet, VinculoClinicaViewSet

router = DefaultRouter()
router.register('clinicas', ClinicaViewSet)
router.register('vinculos', VinculoClinicaViewSet)

urlpatterns = router.urls
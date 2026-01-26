from rest_framework.routers import DefaultRouter
from .views import InmuebleViewSet

router = DefaultRouter()
router.register(r'inmuebles', InmuebleViewSet, basename='inmuebles')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from .views import ExpeditionViewSet

router = DefaultRouter()
router.register('expeditions', ExpeditionViewSet, basename='expedition')

urlpatterns = router.urls

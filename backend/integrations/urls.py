from rest_framework.routers import DefaultRouter

from .views import ApiKeyViewSet, WebhookSubscriptionViewSet

router = DefaultRouter()
router.register("api-keys", ApiKeyViewSet, basename="api-key")
router.register("webhooks", WebhookSubscriptionViewSet, basename="webhook")

urlpatterns = router.urls

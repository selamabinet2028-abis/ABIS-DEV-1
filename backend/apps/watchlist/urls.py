from rest_framework.routers import DefaultRouter

from .views import WatchlistAlertViewSet, WatchlistViewSet

router = DefaultRouter()
router.register("watchlists", WatchlistViewSet, basename="watchlist")
router.register("watchlist-alerts", WatchlistAlertViewSet, basename="watchlist-alert")

urlpatterns = router.urls

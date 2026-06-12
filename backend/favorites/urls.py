from django.urls import path

from favorites.views import FavoritesAPIViews

urlpatterns = [
    path('favorites', FavoritesAPIViews.as_view(), name='favorites'),
    path('admin/favorites', FavoritesAPIViews.as_view(), name='admin-favorites'),
]

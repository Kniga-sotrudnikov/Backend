from django.urls import path

from favorites.views import FavoritesAPIViews

urlpatterns = [
    path('favorites/', FavoritesAPIViews.as_view(), name='favorites'),
    path('favorites/<int:employee_id>/', FavoritesAPIViews.as_view(), name='favorites_detail'),
    path('admin/favorites/', FavoritesAPIViews.as_view(), name='admin-favorites'),
]

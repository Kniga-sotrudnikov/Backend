from django.urls import path

from favorites.views import AdminFavoritesAPIViews, FavoritesAPIViews

urlpatterns = [
    path('favorites/', FavoritesAPIViews.as_view(), name='favorites'),
    path('favorites/<int:employee_id>/', FavoritesAPIViews.as_view(), name='favorites_detail'),
    path('admin/favorites/', AdminFavoritesAPIViews.as_view(), name='admin-favorites'),
    path('admin/favorites/<int:employee_id>/', AdminFavoritesAPIViews.as_view(), name='admin-favorites-detail'),
]

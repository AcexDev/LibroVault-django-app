# Library URLS
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookViewSet, DashboardView, LibraryViewSet

router = DefaultRouter()
router.register('books', BookViewSet, basename='book')
router.register('library', LibraryViewSet, basename='library')

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
]

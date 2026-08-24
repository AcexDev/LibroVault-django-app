# ROOT URLS
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """Index of the API, so the entry points are discoverable from the root."""
    return Response({
        'auth': {
            'register': reverse('register', request=request),
            'login': reverse('login', request=request),
            'refresh': reverse('token-refresh', request=request),
            'logout': reverse('logout', request=request),
            'me': reverse('current-user', request=request),
            'password_reset': reverse('password-reset', request=request),
            'password_reset_confirm': reverse('password-reset-confirm', request=request),
        },
        'books': {
            'list': reverse('book-list', request=request),
            'popular': reverse('book-popular', request=request),
            'search': reverse('book-search', request=request),
            'add': reverse('book-add', request=request),
            'meta': reverse('book-meta', request=request),
        },
        'library': {
            'list': reverse('library-list', request=request),
            'dashboard': reverse('dashboard', request=request),
        },
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/auth/', include('users.urls')),
    path('api/', include('library.urls')),
    # Session login for the DRF browsable API in development.
    path('api-auth/', include('rest_framework.urls')),
]

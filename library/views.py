# Library Views
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import UserBook

from .filters import ORDER_CHOICES, filter_library_queryset
from .models import BOOK_SOURCES, Book
from .serializers import (
    BookCreateSerializer,
    BookDetailSerializer,
    BookSerializer,
    BookUpdateSerializer,
    ExternalBookSerializer,
    PopularBookSerializer,
    ReadingProgressSerializer,
    UserBookSerializer,
)
from .utils import fetch_results, query_input, save_book

PAGE_SIZE = 40  # Google Books results per request


class InUserLibrary(BasePermission):
    """
    Catalogue rows are shared between users, so editing one is only allowed
    when the book is in the requesting user's own library.
    """

    message = "You can only edit books that are in your library."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return UserBook.objects.filter(user=request.user, book=obj).exists()


class BookViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """
    The shared book catalogue.

    Reads are public. Creating a book adds it to the caller's library too, and
    updates are limited to books the caller already has.
    """

    queryset = Book.objects.select_related('booklink').all()
    filterset_fields = ['genre', 'source']
    search_fields = ['title', 'author', 'isbn']
    ordering_fields = ['title', 'author', 'created_at', 'published_year', 'page_count']
    ordering = ['title']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'popular', 'search', 'meta'):
            return [AllowAny()]
        if self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), InUserLibrary()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return BookCreateSerializer
        if self.action in ('update', 'partial_update'):
            return BookUpdateSerializer
        if self.action == 'retrieve':
            return BookDetailSerializer
        if self.action == 'popular':
            return PopularBookSerializer
        if self.action == 'add':
            return ExternalBookSerializer
        return BookSerializer

    @action(detail=False, methods=['get'], url_path='popular', url_name='popular')
    def popular(self, request):
        """The ten most widely held books, manual additions excluded."""
        books = Book.objects.exclude(source="Manual").annotate(
            book_count=Count('userbook')
        ).order_by('-book_count')[:10]
        return Response(self.get_serializer(books, many=True).data)

    @action(detail=False, methods=['get'], url_path='search', url_name='search')
    def search(self, request):
        """
        Proxies a title search to the Google Books API. Paging follows Google's
        own offset scheme via `startIndex`.
        """
        query = request.query_params.get('q')
        try:
            start_index = int(request.query_params.get('startIndex', 0))
        except (TypeError, ValueError):
            return Response(
                {'startIndex': "Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_index = max(start_index, 0)

        query_params = query_input(query)
        if query_params:
            query_params["startIndex"] = start_index

        books = fetch_results(query, query_params) if query else []

        return Response({
            'query': query,
            'count': len(books),
            'start_index': start_index,
            'next_index': start_index + PAGE_SIZE,
            'prev_index': max(start_index - PAGE_SIZE, 0),
            'results': ExternalBookSerializer(books, many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='add', url_name='add',
            permission_classes=[IsAuthenticated])
    def add(self, request):
        """
        Adds an externally sourced book (typically a search result) to the
        catalogue if needed, then to the caller's library as a wishlist entry.
        """
        serializer = ExternalBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_book = save_book(request.user, serializer.validated_data)

        return Response(
            {
                'detail': "Book added successfully!",
                'library_entry': UserBookSerializer(
                    user_book, context={'request': request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='meta', url_name='meta')
    def meta(self, request):
        """Genre, source, status and sort choices for building forms."""
        def pairs(choices):
            return [{'value': value, 'label': label} for value, label in choices]

        return Response({
            'genres': pairs(Book.GENRE_CHOICES),
            'sources': pairs(BOOK_SOURCES),
            'statuses': pairs(UserBook.STATUS_CHOICES),
            'sort_options': pairs(ORDER_CHOICES),
        })


class LibraryViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """
    The caller's own library. Entries are addressed by book id, so the same id
    works here and against /api/books/.
    """

    serializer_class = UserBookSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'book_id'
    lookup_url_kwarg = 'book_id'
    # Filtering is hand-rolled in get_queryset to keep the status/favourite/sort
    # query-string contract stable.
    filter_backends = []

    def get_queryset(self):
        return UserBook.objects.filter(
            user=self.request.user
        ).select_related('book', 'book__booklink')

    def list(self, request, *args, **kwargs):
        queryset = filter_library_queryset(self.get_queryset(), request.query_params)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        response.data = {'detail': "Book succcessfully deleted!"}
        response.status_code = status.HTTP_200_OK
        return response

    @action(detail=True, methods=['post'], url_path='progress', url_name='progress')
    def progress(self, request, book_id=None):
        """
        Records pages read. Reaching the last page marks the book completed,
        anything short of that marks it as being read.
        """
        book = get_object_or_404(Book, pk=book_id)

        serializer = ReadingProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pages_read = serializer.validated_data['pages_read']

        if pages_read > book.page_count:
            return Response(
                {'pages_read': ["Pages Read cannot exceed total pages"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_book, _ = UserBook.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={
                'pages_read': pages_read,
                'status': "completed" if pages_read == book.page_count else "reading",
            },
        )

        return Response({
            'detail': "Reading Progress Updated!",
            'library_entry': UserBookSerializer(
                user_book, context={'request': request}
            ).data,
        })

    @action(detail=True, methods=['post'], url_path='favourite', url_name='favourite')
    def favourite(self, request, book_id=None):
        """Flips the favourite flag on a library entry."""
        user_book = self.get_object()
        user_book.favourite = not user_book.favourite
        user_book.save()

        return Response({
            'detail': (
                "Book added to favourites!" if user_book.favourite
                else "Book removed from favourites!"
            ),
            'library_entry': UserBookSerializer(
                user_book, context={'request': request}
            ).data,
        })


class DashboardView(APIView):
    """
    Everything the old library home page rendered: the caller's books, their
    counts by state, and what is popular across all users.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_books = UserBook.objects.filter(
            user=request.user
        ).select_related('book', 'book__booklink').order_by('-added_at')

        popular_books = Book.objects.exclude(source="Manual").annotate(
            book_count=Count('userbook')
        ).order_by('-book_count')[:10]

        return Response({
            'book_count': user_books.count(),
            'favourites_count': user_books.filter(favourite=True).count(),
            'reading_count': user_books.filter(status='reading').count(),
            'books': UserBookSerializer(
                user_books, many=True, context={'request': request}
            ).data,
            'popular_books': PopularBookSerializer(
                popular_books, many=True, context={'request': request}
            ).data,
        })

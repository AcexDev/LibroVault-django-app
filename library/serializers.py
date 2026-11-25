# Library Serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from users.models import UserBook

from .models import Book, BookLink, BookSourceLink


class BookLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookLink
        fields = ['platforms', 'url']


class BookSourceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookSourceLink
        fields = ['source', 'external_id', 'url']


class BookSerializer(serializers.ModelSerializer):
    """The shared catalogue entry, as returned by every read endpoint."""

    genre_display = serializers.CharField(source='get_genre_display', read_only=True)
    link = serializers.SerializerMethodField()
    source_links = BookSourceLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'google_id', 'title', 'author', 'isbn', 'cover',
            'genre', 'genre_display', 'description', 'source', 'created_at',
            'viewability', 'page_count', 'published_year', 'link', 'source_links',
        ]
        read_only_fields = ['id', 'created_at']

    def get_link(self, obj):
        source_links = list(obj.source_links.all())
        link = next((item for item in source_links if item.source == obj.source), None)
        link = link or next(iter(source_links), None)
        if link and link.url:
            return link.url
        booklink = getattr(obj, 'booklink', None)
        return booklink.url if booklink else None


class PopularBookSerializer(BookSerializer):
    """Adds the number of libraries a book appears in."""

    book_count = serializers.IntegerField(read_only=True)

    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ['book_count']


class BookDetailSerializer(BookSerializer):
    """
    Catalogue entry plus the requesting user's reading state for it. Both
    extra fields are null when the book is not in that user's library.
    """

    pages_read = serializers.SerializerMethodField()
    library_entry = serializers.SerializerMethodField()

    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ['pages_read', 'library_entry']

    def _user_book(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if not hasattr(self, '_cached_user_book'):
            self._cached_user_book = UserBook.objects.filter(
                user=request.user, book=obj
            ).first()
        return self._cached_user_book

    def get_pages_read(self, obj):
        user_book = self._user_book(obj)
        return user_book.pages_read if user_book else None

    def get_library_entry(self, obj):
        user_book = self._user_book(obj)
        if not user_book:
            return None
        return {
            'status': user_book.status,
            'pages_read': user_book.pages_read,
            'favourite': user_book.favourite,
            'added_at': user_book.added_at,
        }


class BookCreateSerializer(serializers.ModelSerializer):
    """
    Manual book entry. Creates the catalogue row and the matching library entry
    for the requesting user in one call.
    """

    status = serializers.ChoiceField(choices=UserBook.STATUS_CHOICES)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'isbn', 'genre', 'published_year',
            'source', 'description', 'status', 'page_count',
        ]

    def create(self, validated_data):
        status = validated_data.pop('status')
        book = Book.objects.create(**validated_data)
        UserBook.objects.create(
            user=self.context['request'].user,
            book=book,
            status=status,
        )
        return book

    def to_representation(self, instance):
        return BookDetailSerializer(instance, context=self.context).data


class BookUpdateSerializer(serializers.ModelSerializer):
    """
    Mirrors the old source-dependent update form: books added manually can be
    fully edited, externally sourced ones only expose reading status.
    """

    MANUAL_FIELDS = ['title', 'author', 'isbn', 'genre', 'description', 'status']
    EXTERNAL_FIELDS = ['status']

    status = serializers.ChoiceField(choices=UserBook.STATUS_CHOICES, required=False)

    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'genre', 'description', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        book = self.instance
        if book is None:
            return
        allowed = self.MANUAL_FIELDS if book.source == 'Manual' else self.EXTERNAL_FIELDS
        for field in list(self.fields):
            if field not in allowed:
                self.fields.pop(field)

    def update(self, instance, validated_data):
        status = validated_data.pop('status', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if status is not None:
            UserBook.objects.update_or_create(
                user=self.context['request'].user,
                book=instance,
                defaults={'status': status},
            )

        return instance

    def to_representation(self, instance):
        return BookDetailSerializer(instance, context=self.context).data


class UserBookSerializer(serializers.ModelSerializer):
    """An entry in a user's library: the book plus their reading state."""

    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(source='book', read_only=True)

    class Meta:
        model = UserBook
        fields = ['id', 'book_id', 'book', 'status', 'pages_read', 'favourite', 'added_at']
        read_only_fields = ['id', 'added_at']

    def validate_pages_read(self, value):
        if value < 0:
            raise serializers.ValidationError("Pages Read cannot be negative")
        book = self.instance.book if self.instance else None
        if book and value > book.page_count:
            raise serializers.ValidationError("Pages Read cannot exceed total pages")
        return value

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            # UserBook.save() runs full_clean(), so model-level errors surface here.
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else list(exc.messages)
            )


class ReadingProgressSerializer(serializers.Serializer):
    """Body for the progress endpoint."""

    pages_read = serializers.IntegerField(min_value=0)


class ExternalBookSerializer(serializers.Serializer):
    """
    A book as it comes back from the Google Books search, and the payload the
    add endpoint accepts so a search result can be sent straight back.
    """

    google_id = serializers.CharField(allow_blank=True, allow_null=True, default='')
    external_id = serializers.CharField(allow_blank=True, max_length=255, required=False, default='')
    source = serializers.ChoiceField(
        choices=[('google', 'Google Books'), ('openlib', 'Open Library'), ('archive', 'Internet Archive')],
        default='google',
    )
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True, allow_null=True, default='')
    authors = serializers.CharField(allow_blank=True, allow_null=True, default='')
    isbn = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    cover = serializers.CharField(allow_blank=True, allow_null=True, default='')
    categories = serializers.CharField(allow_blank=True, allow_null=True, default='')
    description = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    # Google sometimes hands back "#", so this is deliberately not a URLField.
    link = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    viewability = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    page_count = serializers.IntegerField(min_value=0, default=0)
    published_year = serializers.IntegerField(default=0)

    def validate(self, attrs):
        if not attrs.get('external_id') and attrs.get('google_id'):
            attrs['external_id'] = attrs['google_id']
        if attrs.get('source') == 'google' and not attrs.get('google_id'):
            attrs['google_id'] = attrs.get('external_id', '')
        return attrs

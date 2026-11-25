# Users Serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import LIBRARY_VISIBILITY_CHOICES, Notification, Profile, UserBook, UserFollow

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """Bio + Cloudinary avatar. `image` accepts an upload, returns a URL."""

    image = serializers.ImageField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=100)
    library_visibility = serializers.ChoiceField(choices=LIBRARY_VISIBILITY_CHOICES, required=False)

    class Meta:
        model = Profile
        fields = ['image', 'bio', 'library_visibility']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # CloudinaryField's default is a plain URL string, which ImageField
        # cannot build an absolute URI from, so resolve it by hand.
        image = instance.image
        data['image'] = getattr(image, 'url', None) or (str(image) if image else None)
        return data


class UserSerializer(serializers.ModelSerializer):
    """Read-only view of a user with the nested profile attached."""

    profile = ProfileSerializer(read_only=True)
    username_setup_required = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'username_setup_required', 'email', 'first_name', 'last_name', 'date_joined', 'profile']
        read_only_fields = fields

    def get_username_setup_required(self, obj):
        import re
        return bool(re.fullmatch(r'reader_[0-9a-f]{32}', obj.username or '', re.IGNORECASE))


class CommunityReaderSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    book_count = serializers.SerializerMethodField()
    follower_count = serializers.IntegerField(read_only=True)
    can_view_library = serializers.SerializerMethodField()
    library_visibility = serializers.CharField(source='profile.library_visibility', read_only=True)
    bio = serializers.CharField(source='profile.bio', read_only=True)
    avatar = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    follows_you = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'display_name', 'book_count', 'follower_count', 'can_view_library', 'library_visibility', 'bio', 'avatar', 'is_following', 'follows_you']

    def get_display_name(self, obj):
        return obj.username

    def get_avatar(self, obj):
        image = obj.profile.image
        return getattr(image, 'url', None) or (str(image) if image else None)

    def get_is_following(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and UserFollow.objects.filter(
            follower=request.user, following=obj
        ).exists())

    def get_follows_you(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and UserFollow.objects.filter(
            follower=obj, following=request.user
        ).exists())

    def get_can_view_library(self, obj):
        request = self.context.get('request')
        visibility = obj.profile.library_visibility
        if not request or not request.user.is_authenticated:
            return False
        if obj.pk == request.user.pk or visibility == 'everyone':
            return True
        follows = UserFollow.objects.filter(follower=request.user, following=obj).exists()
        if not follows:
            return False
        if visibility == 'followers':
            return True
        return UserFollow.objects.filter(follower=obj, following=request.user).exists()

    def get_book_count(self, obj):
        if not self.get_can_view_library(obj):
            return None
        return getattr(obj, 'book_count', 0)


class CommunityBookSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='book.title', read_only=True)
    author = serializers.CharField(source='book.author', read_only=True)
    cover = serializers.CharField(source='book.cover', read_only=True)
    page_count = serializers.IntegerField(source='book.page_count', read_only=True)
    reader_id = serializers.IntegerField(source='user_id', read_only=True)
    reader_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserBook
        fields = ['id', 'reader_id', 'reader_name', 'title', 'author', 'cover',
                  'status', 'pages_read', 'page_count', 'added_at']


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'actor_name', 'book_title', 'created_at', 'read_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email Already registered with different user")
        return value.strip().lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': "The two password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Email + password, and returns the user alongside the token pair."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Update email, personal name, and profile fields independently.
    """

    username = serializers.CharField(
        required=False, min_length=3, max_length=30,
        validators=[RegexValidator(r'^[\w.@+-]+$', 'Use only letters, numbers, and . @ + - _.')],
    )
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=100)
    image = serializers.ImageField(required=False, write_only=True)
    library_visibility = serializers.ChoiceField(choices=LIBRARY_VISIBILITY_CHOICES, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'bio', 'image', 'library_visibility']

    def validate_username(self, value):
        value = value.strip()
        if not value or value.lower().startswith('reader_'):
            raise serializers.ValidationError('Choose a username that does not use the reserved reader_ prefix.')
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('That username is already taken.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email already registered with another account")
        return value

    def update(self, instance, validated_data):
        bio = validated_data.pop('bio', None)
        image = validated_data.pop('image', None)
        library_visibility = validated_data.pop('library_visibility', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if bio is not None or image is not None or library_visibility is not None:
            profile = instance.profile
            if bio is not None:
                profile.bio = bio
            if image is not None:
                profile.image = image
            if library_visibility is not None:
                profile.library_visibility = library_visibility
            profile.save()

        return instance

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({'uid': "Invalid reset link."})

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': "This reset link is invalid or has expired."})

        try:
            validate_password(attrs['new_password'], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

# Users Serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """Bio + Cloudinary avatar. `image` accepts an upload, returns a URL."""

    image = serializers.ImageField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=100)

    class Meta:
        model = Profile
        fields = ['image', 'bio']

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

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'profile']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email Already registered with different user")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': "The two password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Username + password, and returns the user alongside the token pair."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Replaces UserUpdateForm + ProfileUpdateForm. Every field is optional, so a
    PATCH with just `bio` leaves username and email alone.
    """

    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=100)
    image = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'bio', 'image']

    def validate_username(self, value):
        if not value:
            return self.instance.username
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This Username is Already Taken")
        return value

    def validate_email(self, value):
        if not value:
            return self.instance.email
        if User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email Already registered with different user")
        return value

    def update(self, instance, validated_data):
        bio = validated_data.pop('bio', None)
        image = validated_data.pop('image', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if bio is not None or image is not None:
            profile = instance.profile
            if bio is not None:
                profile.bio = bio
            if image is not None:
                profile.image = image
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

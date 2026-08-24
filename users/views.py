# Users Views
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'detail': f"Account successfully created for {user.username}!",
                'user': UserSerializer(user, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Exchanges username + password for an access/refresh token pair."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """Blacklists the supplied refresh token so it cannot be reused."""

    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            return Response(
                {'detail': "Token is invalid or already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'detail': "Logged out successfully."}, status=status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    GET  -> the signed-in user with their profile
    PATCH-> update username / email / bio / avatar
    """

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {'detail': "Username already taken"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response.data = {
            'detail': "Account Profile successfully updated!",
            'user': response.data,
        }
        return response


class PasswordResetView(APIView):
    """
    Emails a reset link pointing at the frontend. Always answers 200 so the
    endpoint cannot be used to probe which addresses are registered.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            send_mail(
                subject="LibroVault password reset",
                message=(
                    f"Hi {user.username},\n\n"
                    "Use the link below to choose a new password:\n\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return Response(
            {'detail': "If that email is registered, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': "Password has been reset. You can now log in."},
            status=status.HTTP_200_OK,
        )

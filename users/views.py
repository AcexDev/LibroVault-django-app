# Users Views
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .tasks import send_password_reset_email
from .serializers import (
    CommunityBookSerializer,
    CommunityReaderSerializer,
    NotificationSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .social_auth import get_social_profile
from .models import Notification, SocialIdentity, UserBook, UserFollow

logger = logging.getLogger(__name__)
User = get_user_model()


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
                'detail': "Account successfully created.",
                'user': UserSerializer(user, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Exchanges email + password for an access/refresh token pair."""

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
    PATCH-> update email / name / bio / avatar
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
                {'detail': "An account with that email already exists."},
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
            try:
                send_password_reset_email.delay(user.pk)
            except Exception:
                # Keep the response identical for known and unknown addresses.
                logger.exception("Could not queue password reset email.")

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


class SocialLoginView(APIView):
    """Verify Google or GitHub credentials and issue this API's JWT pair."""

    permission_classes = [AllowAny]

    def post(self, request):
        provider = str(request.data.get('provider', '')).strip().lower()
        token = request.data.get('token')
        if provider not in {'google', 'github'} or not isinstance(token, str) or not token:
            return Response(
                {'detail': "Provide provider ('google' or 'github') and token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = get_social_profile(provider, token)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Social authentication failed for %s", provider)
            return Response({'detail': "Could not verify social login."}, status=status.HTTP_400_BAD_REQUEST)

        identity = SocialIdentity.objects.select_related('user').filter(
            provider=provider, provider_uid=profile['uid']
        ).first()
        if identity:
            user = identity.user
        else:
            email = profile['email'].strip().lower()
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    first_name=profile.get('first_name', ''),
                    last_name=profile.get('last_name', ''),
                    password=None,
                )
            elif not user.is_active:
                return Response({'detail': "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)

            try:
                SocialIdentity.objects.create(
                    user=user,
                    provider=provider,
                    provider_uid=profile['uid'],
                    email=email,
                    extra_data=profile.get('extra_data', {}),
                )
            except IntegrityError:
                identity = SocialIdentity.objects.select_related('user').filter(
                    provider=provider, provider_uid=profile['uid']
                ).first()
                if identity is None:
                    return Response(
                        {'detail': "This social provider is already linked to another account."},
                        status=status.HTTP_409_CONFLICT,
                    )
                user = identity.user

        if not user.is_active:
            return Response({'detail': "This account is inactive."}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user, context={'request': request}).data,
        })


class CommunityView(APIView):
    """Discover readers, follow them, and see what they add to their shelves."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        followed_ids = UserFollow.objects.filter(
            follower=request.user
        ).values_list('following_id', flat=True)
        annotations = {
            'book_count': Count('userbook', distinct=True),
            'follower_count': Count('followers', distinct=True),
        }
        following = User.objects.filter(pk__in=followed_ids).annotate(
            **annotations
        ).order_by('first_name', 'pk')
        follower_ids = UserFollow.objects.filter(
            following=request.user
        ).values_list('follower_id', flat=True)
        followers = User.objects.filter(pk__in=follower_ids).annotate(
            **annotations
        ).order_by('first_name', 'pk')
        discover = User.objects.exclude(pk=request.user.pk).exclude(
            pk__in=followed_ids
        ).annotate(**annotations).order_by(
            '-follower_count', 'pk'
        )[:16]
        followed = UserFollow.objects.filter(follower=request.user).select_related('following__profile')
        accessible_ids = [
            relation.following_id for relation in followed
            if relation.following.profile.library_visibility != 'mutuals'
            or UserFollow.objects.filter(follower=relation.following, following=request.user).exists()
        ]
        feed = UserBook.objects.filter(user_id__in=accessible_ids).select_related(
            'user', 'book'
        ).order_by('-added_at')[:30]
        return Response({
            'following': CommunityReaderSerializer(following, many=True, context={'request': request}).data,
            'followers': CommunityReaderSerializer(followers, many=True, context={'request': request}).data,
            'discover': CommunityReaderSerializer(discover, many=True, context={'request': request}).data,
            'feed': CommunityBookSerializer(feed, many=True).data,
        })


class CommunityReaderView(APIView):
    """Return a reader's public library or follow/unfollow that reader."""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        reader = get_object_or_404(
            User.objects.annotate(
                book_count=Count('userbook', distinct=True),
                follower_count=Count('followers', distinct=True),
            ), pk=user_id,
        )
        can_view_library = CommunityReaderSerializer(reader, context={'request': request}).data['can_view_library']
        books = UserBook.objects.filter(user=reader).select_related('book').order_by('-added_at') if can_view_library else UserBook.objects.none()
        is_following = UserFollow.objects.filter(follower=request.user, following=reader).exists()
        follows_you = UserFollow.objects.filter(follower=reader, following=request.user).exists()
        follow_status = 'mutual' if is_following and follows_you else (
            'following' if is_following else 'follows_you' if follows_you else 'not_following'
        )
        return Response({
            'reader': CommunityReaderSerializer(reader, context={'request': request}).data,
            'is_following': is_following,
            'follows_you': follows_you,
            'follow_status': follow_status,
            'can_view_library': can_view_library,
            'books': CommunityBookSerializer(books, many=True).data,
        })

    def post(self, request, user_id):
        reader = get_object_or_404(User, pk=user_id)
        if reader.pk == request.user.pk:
            return Response({'detail': 'You cannot follow yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        _, created = UserFollow.objects.get_or_create(follower=request.user, following=reader)
        if created:
            Notification.objects.create(user=reader, actor=request.user, kind='new_follower')
        return Response({'detail': 'Reader followed.'}, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        UserFollow.objects.filter(follower=request.user, following_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).select_related(
            'actor', 'book'
        )[:30]
        return Response({
            'unread_count': Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
            'results': NotificationSerializer(notifications, many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id=None):
        if notification_id is None:
            Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        else:
            notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
            if notification.read_at is None:
                notification.read_at = timezone.now()
                notification.save(update_fields=['read_at'])
        return Response({'detail': 'Notifications marked as read.'}, status=status.HTTP_200_OK)

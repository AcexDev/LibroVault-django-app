from django.db import models
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from PIL import Image
from library.models import Book
from django.core.exceptions import ValidationError
import os
from cloudinary.models import CloudinaryField


def generate_legacy_username():
    return f'reader_{uuid.uuid4().hex}'


class AccountManager(UserManager):
    """Create accounts with email as their login identifier."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email or '').strip().lower()
        if not email:
            raise ValueError('An email address is required')

        # Keep the legacy username column populated for existing integrations;
        # it is no longer exposed as an account identifier.
        extra_fields.setdefault('username', generate_legacy_username())
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class Account(AbstractUser):
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    username = models.CharField(max_length=150, unique=True, blank=True, default=generate_legacy_username)
    email = models.EmailField(max_length=254, unique=True)
    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'auth_user'

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email or '').strip().lower()
        return super().save(*args, **kwargs)


class SocialIdentity(models.Model):
    PROVIDERS = [('google', 'Google'), ('github', 'GitHub')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_identities')
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    provider_uid = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('provider', 'provider_uid'), name='unique_social_provider_identity'),
            models.UniqueConstraint(fields=('user', 'provider'), name='unique_user_social_provider'),
        ]

    def __str__(self):
        return f'{self.provider}:{self.provider_uid}'

# Create your models here.
LIBRARY_VISIBILITY_CHOICES = [
    ('everyone', 'Everyone'),
    ('followers', 'All followers'),
    ('mutuals', 'Mutual follows'),
]


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = CloudinaryField(default='https://res.cloudinary.com/dtrsdx9x9/image/upload/v1773418355/default_htbobq.jpg', 
                              folder='profile_pics',
                              transformation={
                                'quality': 'auto:low',
                                'fetch_format': 'auto',
                                'width': 200,
                                'height': 200,
                                'crop': 'fill',
                                'gravity': 'face',
                            })
    bio = models.CharField(max_length=100,blank=True)
    library_visibility = models.CharField(
        max_length=12, choices=LIBRARY_VISIBILITY_CHOICES, default='everyone'
    )

    def __str__(self):
        return f"{self.user.email} Profile"
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.image and os.path.exists(self.image.path):
    #         img = Image.open(self.image.path)

    #         if img.height > 300 or img.width > 300:
    #             output_size = (300, 300)
    #             img.thumbnail(output_size)
    #             img.save(self.image.path)

class UserBook(models.Model):
    STATUS_CHOICES = [
        ("reading", "Reading"),
        ("completed", "Completed"),
        ("wishlist", "Wishlist")
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES) 
    added_at = models.DateTimeField(auto_now_add=True)
    pages_read = models.IntegerField(default=0)
    favourite = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("user", "book")

    def clean(self):
        if self.pages_read > self.book.page_count:
            raise ValidationError("Pages Read cannot exceed total pages")

    # OVERRIDE SAVE TO RUN CLEAN METHOD
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ReadingActivity(models.Model):
    """Positive page progress recorded by a reader at a point in time."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    pages_read = models.PositiveIntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at']
        indexes = [models.Index(fields=['user', 'recorded_at'])]

    def __str__(self):
        return f"{self.user} read {self.pages_read} pages of {self.book}"

class UserFollow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")


class Notification(models.Model):
    KIND_CHOICES = [
        ('new_follower', 'New follower'),
        ('book_completed', 'Book completed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications_sent')
    kind = models.CharField(max_length=24, choices=KIND_CHOICES)
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.kind} for {self.user}'

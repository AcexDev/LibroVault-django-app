from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from library.models import Book
from django.core.exceptions import ValidationError
import os

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    bio = models.CharField(max_length=100,blank=True)

    def __str__(self):
        return f"{self.user} Profile"
    
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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

class UserFollow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following"
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

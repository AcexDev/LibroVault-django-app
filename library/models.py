from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

# Create your models here.
BOOK_SOURCES = [
        ("google", "Google Books"),
        ("openlib", "Open Library"),
        ("archive", "Internet Archive"),
        ("publisher", "Publisher"),
        ("Manual", "Personal Addition")
    ]
class Book(models.Model):
    GENRE_CHOICES = [
    ('FIC', 'Fiction'),
    ('NF', 'Non-Fiction'),
    ('SCI', 'Science'),
    ('HIST', 'History'),
    ('BIO', 'Biography'),
    ('FANT', 'Fantasy'),
    ('MYST', 'Mystery'),
    ('ROM', 'Romance'),
    ('TECH', 'Technology'),
    ('SELF', 'Self-Help'),
    ('REL', 'Religion')
]

    google_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=20, null=True, blank=True, help_text="ISBN-10 or ISBN-13")
    cover = models.URLField(blank=True)
    genre = models.CharField(max_length=100, choices=GENRE_CHOICES)
    description = models.TextField(blank=True)
    # owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    source = models.CharField(max_length=20, choices=BOOK_SOURCES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    viewability = models.CharField(max_length=20, blank=True, null=True)
    page_count = models.IntegerField(default=0)
    published_year = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('title', 'author')

    def __str__(self):
        return self.title
     
    def get_absolute_url(self):
        return reverse('book-detail', kwargs={'pk':self.pk})
    

class BookLink(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE)
    platforms = models.CharField(max_length=30, choices=BOOK_SOURCES)
    url = models.URLField()

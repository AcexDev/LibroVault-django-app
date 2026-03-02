import requests
from django.core.management.base import BaseCommand
from library.models import Book, BookLink

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        books = Book.objects.filter(booklink__isnull=False)


        for book in books:
            google_id = book.google_id
            endpoint = f"https://www.googleapis.com/books/v1/volumes/{google_id}"
            query_params = {
                "key": "AIzaSyAhmttZxkbUEsMvD_vgw3UUqu4g58W4f3o",
            }

            response = requests.get(endpoint, params=query_params).json()
            access_info = response.get('accessInfo', {})
            book_link = access_info.get('webReaderLink', '')




            book_link, created = BookLink.objects.update_or_create(
                book=book,
                defaults={
                    'platforms': 'Google Books',
                    'url': book_link
                }
            )

            if created:
                self.stdout.write(f"CREATED link for: {book.title}")
            else:
                self.stdout.write(f"UPDATED link for: {book.title}")




import requests
from django.core.management import BaseCommand
from library.models import Book
from library.utils import api_key

class Command(BaseCommand):
    def handle(self, *args, **options):
        books = Book.objects.all()
        for book in books:
            book_id = book.google_id

            if not book_id:
                self.stdout.write(f"Book ID not found for {book.title}")
                continue
            
            try:
                endpoint = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
                params = {
                    "key": api_key
                }

                response = requests.get(endpoint, params=params).json()

                published_year = response.get('volumeInfo', {}).get('publishedDate', None)
                book.published_year = int(published_year.strip()[:4]) if published_year else 0

                book.save()
                self.stdout.write(f"Year Published Updated for {book.title}")

                
            
            except Exception as e:
                print(f"{e}")





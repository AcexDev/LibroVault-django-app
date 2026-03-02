import requests
from django.core.management.base import BaseCommand
from library.models import Book
from bookcollection import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        books = Book.objects.all()
        

        for book in books:
            book_id = book.google_id
            if not book_id:
                self.stdout.write(f"Google ID not found for {book.title}")
                continue

            try:
                endpoint = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
                query_params = {
                "key": settings.GOOGLE_API_KEY,
            }
                response = requests.get(endpoint, params=query_params).json()
                book_pageCount = response.get('volumeInfo', {}).get('pageCount', 0)

                

                if book_pageCount:
                    book.page_count = book_pageCount
                    book.save()

                    self.stdout.write(f"Updated Pages Count for {book.title}")

                else:
                    self.stdout.write(f"Couldn't Update for {book.title}")
            except Exception as e:
                self.stdout.write(f"Error {e} while updating {book.title}")



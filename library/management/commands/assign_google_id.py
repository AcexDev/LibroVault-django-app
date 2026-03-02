#ASSIGNING GOOGLE ID TO ALL BOOKS

import requests
from django.core.management.base import BaseCommand
from library.models import Book

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        endpoint = "https://www.googleapis.com/books/v1/volumes"
        
        books = Book.objects.filter(google_id__isnull=True)
        for book in books:
            query = f"{book.title} {book.author}"

            if book.isbn:
                query += f" ISBN:{book.isbn}"

            query_params = {
                "key": "AIzaSyAhmttZxkbUEsMvD_vgw3UUqu4g58W4f3o",
                "q": query
            }
            response = requests.get(endpoint, params=query_params).json()

            items = response.get('items')

            if items:
                gid = items[0]['id']
                book.google_id = gid
                book.save()

                self.stdout.write(f"Updated {book.title} ID")

            else:
                self.stdout.write(f"{book.title} ID not found")
            
        
        
        

    
        
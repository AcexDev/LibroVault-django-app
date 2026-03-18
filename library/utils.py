import requests, pprint
from django.contrib.auth.models import User
from library.models import Book, BookLink
from users.models import UserBook
import urllib.parse

from dotenv import load_dotenv
from pathlib import Path
import os
from bookcollection.settings import GOOGLE_API_KEY



endpoint = "https://www.googleapis.com/books/v1/volumes"
api_key = GOOGLE_API_KEY
def query_input(query): 
    if not query:
        return None
    # query = urllib.parse.quote(query)
    search_query = f"intitle:{query}"   
    query_params = {
        "key": api_key,
        "q": search_query,
        "maxResults": 40,
        "startIndex": 0,
    }

    return query_params

def fetch_results(query, query_parameters):
    # query_parameters = query_input(query)
    try:
        response = requests.get(endpoint, params=query_parameters, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Google Books error:", e)
        return []
    data = response.json()
    items = data.get('items', [])
    books = []
    for item in items:
        books.append(query_values(item))

    return books
    


def query_values(item):
    default_thumbnail = "https://nordicdesign.ca/wp-content/uploads/2020/02/book-thumbnail.jpg"
    book_info = item.get('volumeInfo', {})
    book_title = book_info.get('title', 'N/A')
    book_subtitle = book_info.get('subtitle', 'N/A')
    published_date = book_info.get('publishedDate', None)
    book_authors = ", ".join(book_info.get('authors', []))
    book_categories = ", ".join(book_info.get('categories', []))
    book_description = book_info.get('description', None)
    book_thumbnail = book_info.get('imageLinks', {}).get('thumbnail', default_thumbnail)
    book_link = book_info.get('infoLink', '#')
    book_identifier = book_info.get('industryIdentifiers', [])
    book_google_id = item.get('id', '')
    access_info = item.get('accessInfo', {})
    viewability = access_info.get('viewability')
    page_count = book_info.get('pageCount', 0)

    published_date = int(published_date.strip()[:4]) if published_date else 0


    isbn_10=isbn_13=None
    for book in book_identifier:
        if book['type'] == 'ISBN_13':
            isbn_13 = book['identifier']
        elif book['type'] == 'ISBN_10':
            isbn_10 = book['identifier']
    isbn=isbn_13 or isbn_10
    


    book_dict = {
    "book_title" : book_title,
    "book_subtitle" : book_subtitle,
    "published_date" : published_date,
    "book_authors" : book_authors,
    "book_categories" : book_categories,
    "book_description" : book_description,
    "book_thumbnail" : book_thumbnail,
    "book_link": book_link,
    "isbn":isbn,
    'book_google_id': book_google_id,
    'book_viewability': viewability,
    'page_count': int(page_count)
    }

    return book_dict


def book_query():
    query = "Python"
    query_params = query_input(query)
    books = fetch_results(query)
    context = {  
        "books": books,
        "query": query
    }  


def save_book(user:User, book_data:dict):
    title = book_data['book_title']
    author = book_data['book_authors']
    isbn = book_data['isbn']
    book_google_id = book_data['book_google_id']

    if book_google_id:
        book, created = Book.objects.get_or_create(
            google_id=book_google_id,
            defaults={
                "title":title,
                "author": author,
                'isbn': isbn,
                "published_year": book_data["published_date"],
                "cover": book_data['book_thumbnail'],
                # "genre": book_data["book_categories"],
                "genre": "FIC",
                "description": book_data["book_description"],
                "source": "Google Books",
                "viewability": book_data["book_viewability"],
                "page_count": book_data["page_count"]
            }
        )
    else:
        book, created = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                'isbn':isbn,
                'google_id': book_google_id,
                "year_published": book_data["published_date"],
                "cover": book_data['book_thumbnail'],
                # "genre": book_data["book_categories"],
                "genre": "FIC",
                "description": book_data["book_description"],
                "source": "Google Books",
                "viewability": book_data["book_viewability"],
                "page_count" : book_data["page_count"]
            }
        )



    if book_data.get('book_link'):
        BookLink.objects.get_or_create(
            book=book,
            platforms = "Google Books",
            defaults = {
                'url' : book_data.get('book_link')
                }        
        )

    user_book, created = UserBook.objects.get_or_create(
        user = user,
        book = book,
        defaults={
            "status": "wishlist",
            "pages_read": 0
        }
    )

    return user_book



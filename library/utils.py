# Library Utils
import requests
from django.contrib.auth.models import User

from library.models import Book, BookLink
from users.models import UserBook
from bookcollection.settings import GOOGLE_API_KEY

endpoint = "https://www.googleapis.com/books/v1/volumes"
api_key = GOOGLE_API_KEY

DEFAULT_THUMBNAIL = "https://nordicdesign.ca/wp-content/uploads/2020/02/book-thumbnail.jpg"


def query_input(query):
    if not query:
        return None
    search_query = f"intitle:{query}"
    query_params = {
        "key": api_key,
        "q": search_query,
        "maxResults": 40,
        "startIndex": 0,
    }

    return query_params


def fetch_results(query, query_parameters):
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
    """Flattens one Google Books volume into the shape the API returns."""
    book_info = item.get('volumeInfo', {})
    book_title = book_info.get('title', 'N/A')
    book_subtitle = book_info.get('subtitle', 'N/A')
    published_date = book_info.get('publishedDate', None)
    book_authors = ", ".join(book_info.get('authors', []))
    book_categories = ", ".join(book_info.get('categories', []))
    book_description = book_info.get('description', None)
    book_thumbnail = book_info.get('imageLinks', {}).get('thumbnail', DEFAULT_THUMBNAIL)
    book_link = book_info.get('infoLink', '#')
    book_identifier = book_info.get('industryIdentifiers', [])
    book_google_id = item.get('id', '')
    access_info = item.get('accessInfo', {})
    viewability = access_info.get('viewability')
    page_count = book_info.get('pageCount', 0)

    published_date = int(published_date.strip()[:4]) if published_date else 0

    isbn_10 = isbn_13 = None
    for book in book_identifier:
        if book['type'] == 'ISBN_13':
            isbn_13 = book['identifier']
        elif book['type'] == 'ISBN_10':
            isbn_10 = book['identifier']
    isbn = isbn_13 or isbn_10

    book_dict = {
        "google_id": book_google_id,
        "title": book_title,
        "subtitle": book_subtitle,
        "authors": book_authors,
        "isbn": isbn,
        "cover": book_thumbnail,
        "categories": book_categories,
        "description": book_description,
        "link": book_link,
        "viewability": viewability,
        "page_count": int(page_count),
        "published_year": published_date,
    }

    return book_dict


def save_book(user: User, book_data: dict):
    """
    Adds an externally sourced book to the shared catalogue (if it is not
    already there) and puts it in the user's library as a wishlist entry.
    """
    title = book_data['title']
    author = book_data['authors']
    isbn = book_data['isbn']
    book_google_id = book_data['google_id']

    if book_google_id:
        book, created = Book.objects.get_or_create(
            google_id=book_google_id,
            defaults={
                "title": title,
                "author": author,
                'isbn': isbn,
                "published_year": book_data["published_year"],
                "cover": book_data['cover'],
                # "genre": book_data["categories"],
                "genre": "FIC",
                "description": book_data["description"],
                "source": "Google Books",
                "viewability": book_data["viewability"],
                "page_count": book_data["page_count"]
            }
        )
    else:
        book, created = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                'isbn': isbn,
                'google_id': book_google_id,
                "published_year": book_data["published_year"],
                "cover": book_data['cover'],
                # "genre": book_data["categories"],
                "genre": "FIC",
                "description": book_data["description"],
                "source": "Google Books",
                "viewability": book_data["viewability"],
                "page_count": book_data["page_count"]
            }
        )

    if book_data.get('link'):
        BookLink.objects.get_or_create(
            book=book,
            platforms="Google Books",
            defaults={
                'url': book_data.get('link')
            }
        )

    user_book, created = UserBook.objects.get_or_create(
        user=user,
        book=book,
        defaults={
            "status": "wishlist",
            "pages_read": 0
        }
    )

    return user_book

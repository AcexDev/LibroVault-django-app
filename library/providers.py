"""Low-volume, cached adapters for external book discovery APIs."""
import hashlib
import logging

import requests
from django.conf import settings
from django.core.cache import cache

from .utils import DEFAULT_THUMBNAIL

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
PROVIDERS = {
    'google': 'Google Books',
    'openlib': 'Open Library',
    'archive': 'Internet Archive',
}


class BookProviderError(Exception):
    """An external book provider could not complete a search."""


def _headers(source):
    if source == 'openlib':
        email = getattr(settings, 'BOOKS_API_CONTACT_EMAIL', '')
        user_agent = 'LibroVault/1.0'
        if email:
            user_agent += f' (contact: {email})'
    else:
        user_agent = 'LibroVault/1.0 (book discovery)'
    return {'User-Agent': user_agent, 'Accept': 'application/json'}


def _cached_search(source, query, start_index, fetcher):
    cache_key = 'book-search:v1:' + hashlib.sha256(
        f'{source}:{query.strip().casefold()}:{start_index}'.encode('utf-8')
    ).hexdigest()
    try:
        cached = cache.get(cache_key)
    except Exception:
        logger.warning('%s search cache read failed.', PROVIDERS[source], exc_info=True)
        cached = None
    if cached is not None:
        return cached

    try:
        results = fetcher()
    except requests.exceptions.RequestException as exc:
        logger.warning('%s search failed: %s', PROVIDERS[source], exc)
        raise BookProviderError(f"{PROVIDERS[source]} search is temporarily unavailable.") from exc
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        logger.warning('%s returned an invalid response.', PROVIDERS[source], exc_info=True)
        raise BookProviderError(f"{PROVIDERS[source]} returned an unreadable response.") from exc

    try:
        cache.set(cache_key, results, timeout=getattr(settings, 'BOOK_SEARCH_CACHE_TTL', 900))
    except Exception:
        logger.warning('%s search cache write failed.', PROVIDERS[source], exc_info=True)
    return results


def _first(value):
    if isinstance(value, list):
        return value[0] if value else ''
    return value or ''


def _year(value):
    try:
        return int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return 0


def _description(value):
    if isinstance(value, dict):
        return value.get('value') or ''
    return value or ''


def _openlibrary_book(document):
    external_id = document.get('key', '')
    authors = document.get('author_name') or []
    cover_id = document.get('cover_i')
    return {
        'google_id': '',
        'external_id': external_id,
        'source': 'openlib',
        'title': document.get('title') or 'Untitled',
        'subtitle': '',
        'authors': ', '.join(authors) if isinstance(authors, list) else str(authors),
        'isbn': _first(document.get('isbn')),
        'cover': f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg' if cover_id else DEFAULT_THUMBNAIL,
        'categories': '',
        'description': _description(document.get('description')),
        'link': f"https://openlibrary.org/{external_id.lstrip('/')}" if external_id else 'https://openlibrary.org/',
        'viewability': None,
        'page_count': document.get('number_of_pages_median') or 0,
        'published_year': _year(document.get('first_publish_year')),
    }


def search_openlibrary(query, start_index=0):
    def fetch():
        response = requests.get(
            'https://openlibrary.org/search.json',
            params={
                'q': query,
                'fields': 'key,title,author_name,cover_i,first_publish_year,isbn,number_of_pages_median,description',
                'limit': PAGE_SIZE,
                'offset': start_index,
            },
            headers=_headers('openlib'),
            timeout=8,
        )
        response.raise_for_status()
        return [_openlibrary_book(doc) for doc in response.json().get('docs', [])]

    return _cached_search('openlib', query, start_index, fetch)


def _archive_book(document):
    identifier = _first(document.get('identifier'))
    creator = document.get('creator') or []
    return {
        'google_id': '',
        'external_id': identifier,
        'source': 'archive',
        'title': _first(document.get('title')) or 'Untitled',
        'subtitle': '',
        'authors': ', '.join(creator) if isinstance(creator, list) else str(creator),
        'isbn': _first(document.get('isbn')),
        'cover': f'https://archive.org/services/img/{identifier}' if identifier else DEFAULT_THUMBNAIL,
        'categories': '',
        'description': _first(document.get('description')),
        'link': f'https://archive.org/details/{identifier}' if identifier else 'https://archive.org/',
        # The item page owns access and borrowing decisions; search metadata
        # alone does not mean a book can be read or borrowed.
        'viewability': None,
        'page_count': int(_first(document.get('pages')) or 0) if str(_first(document.get('pages')) or '').isdigit() else 0,
        'published_year': _year(_first(document.get('year')) or _first(document.get('date'))),
    }


def search_archive(query, start_index=0):
    # Quote the title as a phrase and escape Lucene string delimiters.
    phrase = query.replace('\\', '\\\\').replace('"', '\\"')
    page = start_index // PAGE_SIZE + 1

    def fetch():
        response = requests.get(
            'https://archive.org/advancedsearch.php',
            params=[
                ('q', f'(title:"{phrase}" OR creator:"{phrase}") AND mediatype:texts'),
                ('fl[]', 'identifier'), ('fl[]', 'title'), ('fl[]', 'creator'),
                ('fl[]', 'year'), ('fl[]', 'date'), ('fl[]', 'description'),
                ('fl[]', 'isbn'), ('fl[]', 'pages'),
                ('rows', PAGE_SIZE), ('page', page), ('output', 'json'),
            ],
            headers=_headers('archive'),
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        return [_archive_book(doc) for doc in data.get('response', {}).get('docs', [])]

    return _cached_search('archive', query, start_index, fetch)


def search_google(query, start_index=0):
    """Preserve the existing Google search response mapper and cache."""
    from .utils import fetch_results, query_input

    params = query_input(query)
    if params:
        params['startIndex'] = start_index
    cache_key = 'book-search:v1:' + hashlib.sha256(
        f'google:{query.strip().casefold()}:{start_index}'.encode('utf-8')
    ).hexdigest()
    try:
        books = cache.get(cache_key)
    except Exception:
        logger.warning('Google Books search cache read failed.', exc_info=True)
        books = None
    if books is None:
        books = fetch_results(query, params)
        try:
            cache.set(cache_key, books, timeout=settings.GOOGLE_BOOKS_CACHE_TTL)
        except Exception:
            logger.warning('Google Books search cache write failed.', exc_info=True)
    return [
        {**book, 'external_id': book.get('google_id'), 'source': 'google'}
        for book in books
    ]


SEARCHERS = {
    'google': search_google,
    'openlib': search_openlibrary,
    'archive': search_archive,
}

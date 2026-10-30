# Library API Tests
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Book, BookLink
from users.models import UserBook


def make_book(**overrides):
    fields = {
        'title': 'Dune',
        'author': 'Frank Herbert',
        'genre': 'SCI',
        'source': 'Google Books',
        'google_id': 'abc123',
        'page_count': 400,
        'published_year': 1965,
    }
    fields.update(overrides)
    return Book.objects.create(**fields)


class BookCatalogueTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.book = make_book()

    def test_list_is_public(self):
        response = self.client.get(reverse('book-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_detail_exposes_booklink_url(self):
        BookLink.objects.create(book=self.book, platforms='Google Books', url='https://example.com/dune')
        response = self.client.get(reverse('book-detail', args=[self.book.pk]))
        self.assertEqual(response.data['link'], 'https://example.com/dune')

    def test_detail_omits_reading_state_for_anonymous(self):
        response = self.client.get(reverse('book-detail', args=[self.book.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['pages_read'])
        self.assertIsNone(response.data['library_entry'])

    def test_detail_includes_reading_state_for_owner(self):
        UserBook.objects.create(user=self.user, book=self.book, status='reading', pages_read=120)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('book-detail', args=[self.book.pk]))
        self.assertEqual(response.data['pages_read'], 120)
        self.assertEqual(response.data['library_entry']['status'], 'reading')

    def test_search_filter_matches_title(self):
        make_book(title='Neuromancer', author='William Gibson', google_id='xyz789')
        response = self.client.get(reverse('book-list'), {'search': 'Neuro'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Neuromancer')

    def test_popular_excludes_manual_and_counts_owners(self):
        manual = make_book(title='My Notes', author='Ada', source='Manual', google_id=None)
        UserBook.objects.create(user=self.user, book=self.book, status='reading')
        UserBook.objects.create(user=self.user, book=manual, status='reading')

        response = self.client.get(reverse('book-popular'))
        titles = [book['title'] for book in response.data]
        self.assertIn('Dune', titles)
        self.assertNotIn('My Notes', titles)
        self.assertEqual(response.data[0]['book_count'], 1)

    def test_meta_lists_choices(self):
        response = self.client.get(reverse('book-meta'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn({'value': 'SCI', 'label': 'Science'}, response.data['genres'])
        self.assertIn({'value': 'wishlist', 'label': 'Wishlist'}, response.data['statuses'])
        self.assertIn('sort_options', response.data)


class ManualBookCreateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)

    def test_creates_book_and_library_entry(self):
        response = self.client.post(reverse('book-list'), {
            'title': 'Hand Written',
            'author': 'Ada',
            'genre': 'NF',
            'source': 'Manual',
            'description': 'Notes',
            'page_count': 50,
            'published_year': 2024,
            'status': 'reading',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        book = Book.objects.get(title='Hand Written')
        entry = UserBook.objects.get(user=self.user, book=book)
        self.assertEqual(entry.status, 'reading')

    def test_requires_status(self):
        response = self.client.post(reverse('book-list'), {
            'title': 'Hand Written',
            'author': 'Ada',
            'genre': 'NF',
            'source': 'Manual',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_rejects_duplicate_title_author(self):
        make_book(title='Dune', author='Frank Herbert')
        response = self.client.post(reverse('book-list'), {
            'title': 'Dune',
            'author': 'Frank Herbert',
            'genre': 'SCI',
            'source': 'Manual',
            'status': 'reading',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse('book-list'), {'title': 'x', 'author': 'y'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BookUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)

    def test_external_book_only_accepts_status(self):
        book = make_book(source='Google Books')
        UserBook.objects.create(user=self.user, book=book, status='wishlist')

        response = self.client.patch(reverse('book-detail', args=[book.pk]), {
            'title': 'Renamed',
            'status': 'reading',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        book.refresh_from_db()
        self.assertEqual(book.title, 'Dune')
        self.assertEqual(UserBook.objects.get(user=self.user, book=book).status, 'reading')

    def test_manual_book_accepts_full_edit(self):
        book = make_book(title='My Notes', source='Manual', google_id=None)
        UserBook.objects.create(user=self.user, book=book, status='wishlist')

        response = self.client.patch(reverse('book-detail', args=[book.pk]), {
            'title': 'My Better Notes',
            'genre': 'HIST',
            'status': 'completed',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        book.refresh_from_db()
        self.assertEqual(book.title, 'My Better Notes')
        self.assertEqual(book.genre, 'HIST')

    def test_rejects_edit_of_book_not_in_library(self):
        book = make_book(source='Manual', google_id=None)
        response = self.client.patch(reverse('book-detail', args=[book.pk]), {'title': 'Nope'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        book.refresh_from_db()
        self.assertEqual(book.title, 'Dune')


class LibraryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.other = User.objects.create_user('grace', 'grace@example.com', 'pw')
        self.client.force_authenticate(user=self.user)

        self.dune = make_book()
        self.neuro = make_book(title='Neuromancer', author='William Gibson', google_id='xyz789')

        self.dune_entry = UserBook.objects.create(
            user=self.user, book=self.dune, status='reading', pages_read=100
        )
        self.neuro_entry = UserBook.objects.create(
            user=self.user, book=self.neuro, status='wishlist', favourite=True
        )

    def test_lists_only_own_entries(self):
        UserBook.objects.create(user=self.other, book=self.dune, status='reading')
        response = self.client.get(reverse('library-list'))
        self.assertEqual(response.data['count'], 2)

    def test_filters_by_status(self):
        response = self.client.get(reverse('library-list'), {'status': 'reading'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['book']['title'], 'Dune')

    def test_filters_by_favourite(self):
        response = self.client.get(reverse('library-list'), {'favourite': '1'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['book']['title'], 'Neuromancer')

    def test_sorts_by_title(self):
        response = self.client.get(reverse('library-list'), {'sort': 'title_asc'})
        titles = [entry['book']['title'] for entry in response.data['results']]
        self.assertEqual(titles, ['Dune', 'Neuromancer'])

        response = self.client.get(reverse('library-list'), {'sort': 'title_desc'})
        titles = [entry['book']['title'] for entry in response.data['results']]
        self.assertEqual(titles, ['Neuromancer', 'Dune'])

    def test_defaults_to_newest_first(self):
        response = self.client.get(reverse('library-list'))
        titles = [entry['book']['title'] for entry in response.data['results']]
        self.assertEqual(titles, ['Neuromancer', 'Dune'])

    def test_retrieve_by_book_id(self):
        response = self.client.get(reverse('library-detail', args=[self.dune.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['book_id'], self.dune.pk)

    def test_patch_updates_status(self):
        response = self.client.patch(
            reverse('library-detail', args=[self.dune.pk]), {'status': 'completed'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.dune_entry.refresh_from_db()
        self.assertEqual(self.dune_entry.status, 'completed')

    def test_patch_rejects_pages_beyond_total(self):
        response = self.client.patch(
            reverse('library-detail', args=[self.dune.pk]), {'pages_read': 5000}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pages_read', response.data)

    def test_delete_removes_entry_but_keeps_book(self):
        response = self.client.delete(reverse('library-detail', args=[self.dune.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserBook.objects.filter(user=self.user, book=self.dune).exists())
        self.assertTrue(Book.objects.filter(pk=self.dune.pk).exists())

    def test_cannot_touch_another_users_entry(self):
        third = make_book(title='Foundation', author='Isaac Asimov', google_id='foundation')
        UserBook.objects.create(user=self.other, book=third, status='reading')
        response = self.client.delete(reverse('library-detail', args=[third.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReadingProgressTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)
        self.book = make_book(page_count=400)
        self.entry = UserBook.objects.create(user=self.user, book=self.book, status='wishlist')

    def test_partial_progress_marks_reading(self):
        response = self.client.post(
            reverse('library-progress', args=[self.book.pk]), {'pages_read': 200}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.pages_read, 200)
        self.assertEqual(self.entry.status, 'reading')

    def test_reaching_last_page_marks_completed(self):
        self.client.post(
            reverse('library-progress', args=[self.book.pk]), {'pages_read': 400}
        )
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, 'completed')

    def test_rejects_progress_beyond_total(self):
        response = self.client.post(
            reverse('library-progress', args=[self.book.pk]), {'pages_read': 401}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.pages_read, 0)

    def test_favourite_toggles_both_ways(self):
        url = reverse('library-favourite', args=[self.book.pk])

        self.client.post(url)
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.favourite)

        self.client.post(url)
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.favourite)

    def test_favourite_404s_when_not_in_library(self):
        other_book = make_book(title='Foundation', author='Isaac Asimov', google_id='foundation')
        response = self.client.post(reverse('library-favourite', args=[other_book.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


GOOGLE_VOLUME = {
    'id': 'abc123',
    'volumeInfo': {
        'title': 'Dune',
        'subtitle': 'A novel',
        'authors': ['Frank Herbert'],
        'categories': ['Fiction'],
        'description': 'Desert planet.',
        'publishedDate': '1965-08-01',
        'pageCount': 412,
        'imageLinks': {'thumbnail': 'https://example.com/dune.jpg'},
        'infoLink': 'https://example.com/dune',
        'industryIdentifiers': [
            {'type': 'ISBN_10', 'identifier': '0441013597'},
            {'type': 'ISBN_13', 'identifier': '9780441013593'},
        ],
    },
    'accessInfo': {'viewability': 'PARTIAL'},
}


class SearchTests(APITestCase):
    @patch('library.utils.requests.get')
    def test_flattens_google_results(self, mock_get):
        mock_get.return_value.json.return_value = {'items': [GOOGLE_VOLUME]}
        mock_get.return_value.raise_for_status.return_value = None

        response = self.client.get(reverse('book-search'), {'q': 'dune'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

        book = response.data['results'][0]
        self.assertEqual(book['title'], 'Dune')
        self.assertEqual(book['authors'], 'Frank Herbert')
        self.assertEqual(book['isbn'], '9780441013593')
        self.assertEqual(book['published_year'], 1965)
        self.assertEqual(book['page_count'], 412)
        self.assertEqual(book['viewability'], 'PARTIAL')

    @patch('library.utils.requests.get')
    def test_paging_indexes(self, mock_get):
        mock_get.return_value.json.return_value = {'items': []}
        mock_get.return_value.raise_for_status.return_value = None

        response = self.client.get(reverse('book-search'), {'q': 'dune', 'startIndex': '40'})
        self.assertEqual(response.data['start_index'], 40)
        self.assertEqual(response.data['next_index'], 80)
        self.assertEqual(response.data['prev_index'], 0)
        self.assertEqual(mock_get.call_args.kwargs['params']['startIndex'], 40)

    def test_blank_query_returns_nothing_without_calling_google(self):
        with patch('library.utils.requests.get') as mock_get:
            response = self.client.get(reverse('book-search'))
        self.assertEqual(response.data['results'], [])
        mock_get.assert_not_called()

    @patch('library.utils.requests.get', side_effect=Exception('boom'))
    def test_search_is_public(self, _mock_get):
        response = self.client.get(reverse('book-search'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AddExternalBookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)
        self.payload = {
            'google_id': 'abc123',
            'title': 'Dune',
            'authors': 'Frank Herbert',
            'isbn': '9780441013593',
            'cover': 'https://example.com/dune.jpg',
            'description': 'Desert planet.',
            'link': 'https://example.com/dune',
            'viewability': 'PARTIAL',
            'page_count': 412,
            'published_year': 1965,
        }

    def test_creates_book_link_and_wishlist_entry(self):
        response = self.client.post(reverse('book-add'), self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        book = Book.objects.get(google_id='abc123')
        self.assertEqual(book.title, 'Dune')
        self.assertEqual(book.author, 'Frank Herbert')
        self.assertEqual(book.published_year, 1965)
        self.assertEqual(book.page_count, 412)

        self.assertEqual(BookLink.objects.get(book=book).url, 'https://example.com/dune')

        entry = UserBook.objects.get(user=self.user, book=book)
        self.assertEqual(entry.status, 'wishlist')
        self.assertEqual(entry.pages_read, 0)

    def test_second_user_reuses_the_same_book(self):
        self.client.post(reverse('book-add'), self.payload)

        grace = User.objects.create_user('grace', 'grace@example.com', 'pw')
        self.client.force_authenticate(user=grace)
        self.client.post(reverse('book-add'), self.payload)

        self.assertEqual(Book.objects.filter(google_id='abc123').count(), 1)
        self.assertEqual(UserBook.objects.filter(book__google_id='abc123').count(), 2)

    def test_adding_twice_is_idempotent(self):
        self.client.post(reverse('book-add'), self.payload)
        response = self.client.post(reverse('book-add'), self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserBook.objects.filter(user=self.user).count(), 1)

    def test_handles_result_without_google_id(self):
        response = self.client.post(
            reverse('book-add'), {**self.payload, 'google_id': ''}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(title='Dune', author='Frank Herbert')
        self.assertEqual(book.published_year, 1965)

    def test_requires_title(self):
        payload = {**self.payload}
        del payload['title']
        response = self.client.post(reverse('book-add'), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse('book-add'), self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DashboardTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)

        dune = make_book()
        neuro = make_book(title='Neuromancer', author='William Gibson', google_id='xyz789')
        UserBook.objects.create(user=self.user, book=dune, status='reading')
        UserBook.objects.create(user=self.user, book=neuro, status='wishlist', favourite=True)

    def test_returns_counts_books_and_popular(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['book_count'], 2)
        self.assertEqual(response.data['favourites_count'], 1)
        self.assertEqual(response.data['reading_count'], 1)
        self.assertEqual(len(response.data['books']), 2)
        self.assertEqual(len(response.data['popular_books']), 2)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class APIIndexTests(APITestCase):
    """The root index reverses every entry point, so it catches renamed routes."""

    def test_root_is_public_and_lists_sections(self):
        response = self.client.get(reverse('api-root'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {'auth', 'books', 'library'})
        self.assertTrue(response.data['books']['search'].endswith('/api/books/search/'))

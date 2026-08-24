# Users API Tests
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RegisterTests(APITestCase):
    payload = {
        'username': 'ada',
        'email': 'ada@example.com',
        'password': 'sup3r-s3cret-pw',
        'password2': 'sup3r-s3cret-pw',
    }

    def test_creates_user(self):
        response = self.client.post(reverse('register'), self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'ada')
        self.assertTrue(User.objects.filter(username='ada').exists())

    def test_profile_created_by_signal(self):
        self.client.post(reverse('register'), self.payload)
        self.assertIsNotNone(User.objects.get(username='ada').profile)

    def test_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse('register'), {**self.payload, 'password2': 'something-else'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)

    def test_rejects_duplicate_email(self):
        User.objects.create_user('grace', 'ada@example.com', 'pw')
        response = self.client.post(reverse('register'), self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'sup3r-s3cret-pw')

    def login(self):
        return self.client.post(
            reverse('login'), {'username': 'ada', 'password': 'sup3r-s3cret-pw'}
        )

    def test_login_returns_token_pair_and_user(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'ada')

    def test_login_rejects_bad_password(self):
        response = self.client.post(
            reverse('login'), {'username': 'ada', 'password': 'wrong'}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_authenticates_requests(self):
        token = self.login().data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('current-user'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'ada')

    def test_logout_blacklists_refresh_token(self):
        tokens = self.login().data

        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('logout'), {'refresh': tokens['refresh']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refreshed = self.client.post(reverse('token-refresh'), {'refresh': tokens['refresh']})
        self.assertEqual(refreshed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('current-user'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw')
        self.client.force_authenticate(user=self.user)

    def test_updates_bio_without_touching_username(self):
        response = self.client.patch(reverse('current-user'), {'bio': 'Reads a lot'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'ada')
        self.assertEqual(self.user.profile.bio, 'Reads a lot')

    def test_updates_username_and_email(self):
        response = self.client.patch(reverse('current-user'), {
            'username': 'ada-l',
            'email': 'ada.l@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'ada-l')
        self.assertEqual(self.user.email, 'ada.l@example.com')

    def test_rejects_taken_username(self):
        User.objects.create_user('grace', 'grace@example.com', 'pw')
        response = self.client.patch(reverse('current-user'), {'username': 'grace'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_rejects_taken_email(self):
        User.objects.create_user('grace', 'grace@example.com', 'pw')
        response = self.client.patch(reverse('current-user'), {'email': 'grace@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'old-password-123')

    def test_sends_email_for_known_address(self):
        response = self.client.post(reverse('password-reset'), {'email': 'ada@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset-password', mail.outbox[0].body)

    def test_stays_quiet_for_unknown_address(self):
        response = self.client.post(reverse('password-reset'), {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def _reset_credentials(self):
        self.client.post(reverse('password-reset'), {'email': 'ada@example.com'})
        link = next(w for w in mail.outbox[0].body.split() if 'reset-password' in w)
        uid, token = link.rstrip('/').split('/')[-2:]
        return uid, token

    def test_confirm_sets_new_password(self):
        uid, token = self._reset_credentials()
        response = self.client.post(reverse('password-reset-confirm'), {
            'uid': uid,
            'token': token,
            'new_password': 'brand-new-pw-456',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brand-new-pw-456'))

    def test_confirm_rejects_bad_token(self):
        uid, _ = self._reset_credentials()
        response = self.client.post(reverse('password-reset-confirm'), {
            'uid': uid,
            'token': 'not-a-real-token',
            'new_password': 'brand-new-pw-456',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)

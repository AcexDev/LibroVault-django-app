"""Provider credential verification for the email-first social login API."""

from django.conf import settings


def _google_profile(token):
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    audience = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    if not audience:
        raise ValueError('Google sign-in is not configured on this server.')

    claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience)
    email = claims.get('email', '').strip().lower()
    if not claims.get('sub') or not email or claims.get('email_verified') is not True:
        raise ValueError('Google did not provide a verified email address.')

    return {
        'uid': claims['sub'],
        'email': email,
        'first_name': claims.get('given_name', ''),
        'last_name': claims.get('family_name', ''),
        'extra_data': {'picture': claims.get('picture', '')},
    }


def _github_profile(token):
    import requests

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
    if response.status_code != 200:
        raise ValueError('GitHub could not verify this sign-in.')
    account = response.json()

    email_response = requests.get('https://api.github.com/user/emails', headers=headers, timeout=10)
    if email_response.status_code != 200:
        raise ValueError('GitHub did not return an accessible email address.')
    verified_emails = [item for item in email_response.json() if item.get('verified')]
    chosen_email = next((item for item in verified_emails if item.get('primary')), None)
    if chosen_email is None and verified_emails:
        chosen_email = verified_emails[0]
    if not account.get('id') or chosen_email is None:
        raise ValueError('A verified GitHub email address is required to sign in.')

    name = (account.get('name') or '').strip()
    first_name, _, last_name = name.partition(' ')
    return {
        'uid': str(account['id']),
        'email': chosen_email['email'].strip().lower(),
        'first_name': first_name,
        'last_name': last_name,
        'extra_data': {'login': account.get('login', ''), 'avatar_url': account.get('avatar_url', '')},
    }


def get_social_profile(provider, token):
    if provider == 'google':
        return _google_profile(token)
    if provider == 'github':
        return _github_profile(token)
    raise ValueError('Unsupported social login provider.')

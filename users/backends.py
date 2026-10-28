from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate Django forms with either the account username or email.

    ModelBackend remains responsible for password checking and account status,
    so this works with Django admin's standard username field as well as email.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        username = username or kwargs.get(UserModel.USERNAME_FIELD)
        if username and password and '@' in username:
            matches = UserModel._default_manager.filter(email__iexact=username)
            if matches.count() == 1:
                username = matches.get().get_username()

        return super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs,
        )

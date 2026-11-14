from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """Compatibility backend that treats the submitted identifier as email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get(UserModel.USERNAME_FIELD) or username
        return super().authenticate(
            request,
            username=email,
            password=password,
        )

import logging
import smtplib

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id):
    """Send a password reset message without putting its token in the queue."""
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
    try:
        send_mail(
            subject="LibroVault password reset",
            message=(
                f"Hi {user.username},\n\n"
                "Use the link below to choose a new password:\n\n"
                f"{reset_url}\n\n"
                "If you did not request this, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Password reset email delivery failed; retrying.")
        raise self.retry(exc=exc)

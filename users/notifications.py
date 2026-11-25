from .models import Notification, UserFollow


def notify_followers_of_completion(actor, book):
    """Notify followers who are allowed to view this reader's library."""
    visibility = actor.profile.library_visibility
    follower_ids = list(UserFollow.objects.filter(
        following=actor
    ).values_list('follower_id', flat=True))

    if visibility == 'mutuals':
        mutual_ids = UserFollow.objects.filter(
            follower=actor, following_id__in=follower_ids
        ).values_list('following_id', flat=True)
        follower_ids = list(mutual_ids)

    Notification.objects.bulk_create([
        Notification(user_id=follower_id, actor=actor, kind='book_completed', book=book)
        for follower_id in follower_ids
    ])

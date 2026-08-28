from .models import Notification


def notify(user, notification_type: str, message: str, link_path: str = "") -> Notification:
    return Notification.objects.create(
        user=user, notification_type=notification_type, message=message, link_path=link_path,
    )

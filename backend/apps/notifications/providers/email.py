from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone

def send_email(notification):
    """
    Raises exception on failure.
    Caller (dispatcher) handles retry / DLQ.
    """

    payload = notification.payload
    subject = payload.get("subject", "Notification")
    body = payload.get("body", "")
    html_body = payload.get("html", None)

    if not notification.user.email:
        raise ValueError("User has no email")

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notification.user.email],
    )

    if html_body:
        msg.attach_alternative(html_body, "text/html")

    msg.send(fail_silently=False)

    return {
        "channel": "email",
        "sent_at": timezone.now().isoformat(),
        "to": notification.user.email,
    }

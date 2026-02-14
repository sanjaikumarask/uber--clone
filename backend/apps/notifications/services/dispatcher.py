from .router import route_notification
from ..models import Notification

def dispatch(notification: Notification) -> None:
    """
    Attempt delivery.
    - MUST raise exception on failure
    - MUST NOT mutate DB state
    """
    route_notification(notification)

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.drivers.models import Driver
from apps.users.models import User

@receiver(post_save, sender=User)
def create_driver_profile(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == User.ROLE_DRIVER:
        Driver.objects.get_or_create(user=instance)
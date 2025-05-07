from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import *

@receiver(pre_save, sender=Student)
def normalize_email(sender, instance, **kwargs):
    instance.email = instance.email.lower()

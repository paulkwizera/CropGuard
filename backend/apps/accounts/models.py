from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Farmer account. Extra profile fields help tailor weather advice and language."""

    class Language(models.TextChoices):
        KINYARWANDA = "rw", "Kinyarwanda"
        ENGLISH = "en", "English"
        FRENCH = "fr", "Français"

    phone = models.CharField(max_length=20, blank=True)
    district = models.CharField(max_length=60, blank=True)
    preferred_language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.KINYARWANDA
    )

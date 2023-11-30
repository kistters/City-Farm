from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from .managers import CitizenManager, FarmerManager


class User(AbstractUser):
    is_citizen = models.BooleanField(_('is Citizen'), default=False)
    is_farmer = models.BooleanField(_('is Farmer'), default=False)


class Citizen(User):
    objects = CitizenManager()

    class Meta:
        proxy = True


class Farmer(User):
    objects = FarmerManager()

    class Meta:
        proxy = True

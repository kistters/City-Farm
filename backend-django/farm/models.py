from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CommodityManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Commodity(models.Model):
    name = models.CharField(_("name"), max_length=150, unique=True)
    objects = CommodityManager()

    class Meta:
        verbose_name = _("Commodity")
        verbose_name_plural = _("Commodities")

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class Food(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='food_related')
    farmer_owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='produced_food')
    produced_at = models.DateTimeField()

    class Meta:
        verbose_name = _("Food")
        verbose_name_plural = _("Food")

    def __str__(self):
        return f"{self.commodity}"

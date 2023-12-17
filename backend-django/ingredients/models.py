from django.db import models
from django.contrib.auth.models import User
from django.db.models import CheckConstraint, Q, F


class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    producer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='produced_ingredients')
    produced_at = models.DateTimeField()
    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bought_ingredients', null=True, blank=True)
    bought_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(producer=F('buyer')),
                name='producer_and_buyer_must_differ',
            ),
        ]

    def __str__(self):
        text = f"{self.name} produced by {self.producer}"
        if self.buyer:
            text += f" bought by {self.buyer}"

        return text

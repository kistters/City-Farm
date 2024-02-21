from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class Job(models.Model):
    name = models.CharField(_("name"), max_length=150, unique=True)

    class Meta:
        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")

    def __str__(self):
        return self.name


class Money(models.Model):
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name='job_related')
    citizen_owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='earned_money')
    produced_at = models.DateTimeField()

    class Meta:
        verbose_name = _("Money")
        verbose_name_plural = _("Money")

    def __str__(self):
        return f"{self.job}"

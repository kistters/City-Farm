from django.contrib import admin

from .models import Job, Money


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    pass


@admin.register(Money)
class MoneyAdmin(admin.ModelAdmin):
    pass

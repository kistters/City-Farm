from django.contrib import admin

from .models import Commodity, Food


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    pass


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    pass

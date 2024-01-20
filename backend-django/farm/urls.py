from django.urls import path

from farm.views import CommodityList, FoodAPIView, FoodSummaryAPIView

urlpatterns = [
    path('commodities/', CommodityList.as_view(), name='commodity-list'),
    path('food/', FoodAPIView.as_view(), name='food-view'),
    path('food/summary/', FoodSummaryAPIView.as_view(), name='food-summary'),
]

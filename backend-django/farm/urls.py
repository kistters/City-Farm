from django.urls import path

from farm.views import CommodityList, FoodAPIView, SummaryAPIView

urlpatterns = [
    path('commodities/', CommodityList.as_view(), name='commodity-list'),
    path('food/', FoodAPIView.as_view(), name='food-view'),
    path('summary/', SummaryAPIView.as_view(), name='summary-view'),
]

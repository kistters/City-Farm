from django.urls import path

from api_layer.views import (
    LogoutView, LoginView, RegisterView,
    CommodityListView, ProduceFoodAPIView, CommoditySummaryAPIView,
    JobListView, DoTheWorkAPIView, JobSummaryAPIView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    # farm
    path('commodities/', CommodityListView.as_view(), name='commodity-list'),
    path('produce-food/', ProduceFoodAPIView.as_view(), name='produce-food'),
    path('commodity-summary/', CommoditySummaryAPIView.as_view(), name='commodity-summary'),
    # city
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('do-the-work/', DoTheWorkAPIView.as_view(), name='do-the-work'),
    path('job-summary/', JobSummaryAPIView.as_view(), name='job-summary'),
]

from django.urls import path

from . import views

urlpatterns = [
    path('', views.user_list, name='user-list'),
    path('<slug:username>', views.user_detail, name='user-detail'),
]
from django.urls import path

from api_layer.views import LogoutView, LoginView, RegisterView, IngredientProduceView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('produce-ingredient/', IngredientProduceView.as_view(), name='produce-ingredient'),
]

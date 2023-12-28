from django.urls import path

from api_layer.views import LogoutView, LoginView, RegisterView, ProduceIngredientView, BuyIngredientView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('produce-ingredient/', ProduceIngredientView.as_view(), name='produce-ingredient'),
    path('buy-ingredient/', BuyIngredientView.as_view(), name='buy-ingredient'),
]

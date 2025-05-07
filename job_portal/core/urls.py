from django.urls import path
from .views import register,home

urlpatterns = [
    path('register/', register, name='register'),
    path('', home, name='home'),
]

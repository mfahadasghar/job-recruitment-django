from django.urls import path
from .views import register,CustomLoginView,dashboard
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
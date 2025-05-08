from django.shortcuts import render, redirect
from .forms import UserRegisterForm,UserLoginForm
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})


def home(request):
    return HttpResponse("Welcome to Job Portal!")

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = UserLoginForm
    

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')
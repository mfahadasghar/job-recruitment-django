from django.shortcuts import render, redirect
from .forms import UserRegisterForm
from django.http import HttpResponse

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
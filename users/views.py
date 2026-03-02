from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm, UserLoginForm
from django.db import IntegrityError
from django.contrib.auth import login
# Create your views here.

def login_view(request):
    if request.user.is_authenticated:
        return redirect("library-home")  # or wherever

    form = UserLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Logged in successfully!")
        return redirect("library-home")
    return render(request, "users/login.html", {"form": form})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"Account successfully created for {username}!")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form':form})

@login_required
def profile(request):
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            try:
                u_form.save()
                p_form.save()
                messages.success(request, f"Account Profile successfully updated!")
                return redirect('profile')
            except IntegrityError:
                messages.error('request', 'Username already taken')


    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        
    context = {
            'u_form': u_form,
            'p_form': p_form
        }

    return render(request, 'users/profile.html', context)

@login_required
def account(request):
    return render(request, 'users/account.html')

def about(request):
    return render(request, 'library/about.html')


from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth import authenticate

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    age = forms.IntegerField()
    class Meta:
        model = User
        fields = ['username', 'email', 'age', 'password1','password2']

class UserUpdateForm(forms.ModelForm):
    username = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    class Meta:
        model = User
        fields = ['username', 'email']
    def clean_username(self):
        username = self.cleaned_data.get('username')

        #To Check If Existing Users own that username
        if User.objects.filter(username=username).exclude(pk=self.instance.id).exists():
            raise forms.ValidationError("This Username is Already Taken")

        #Return Current username if no username entered        
        if not username:
            return self.instance.username
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.id).exists():
            raise forms.ValidationError("Email Already registered with different user")

        if not email:
            return self.instance.email
        return email

class ProfileUpdateForm(forms.ModelForm):
    # image = forms.ImageField(required=False)
    bio = forms.CharField(required=False)
    class Meta:
        model = Profile
        fields = ['bio', 'image']
        widgets = {
        'image': forms.FileInput()
        }

class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data =  super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('passeord')

        if email and password:
            user = authenticate(username=email, password=password)

            if user is None:
                raise forms.ValidationError('Invalid Email or Password')
            
        return cleaned_data
    
    def get_user(self):
        return getattr(self, "user", None)
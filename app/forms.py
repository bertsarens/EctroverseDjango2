from django import forms
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class UploadImageForm(forms.Form):
    title = forms.CharField(max_length=50)
    image = forms.ImageField()

class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ["username","email","password1","password2"]

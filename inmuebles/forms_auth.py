from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ingrese su usuario"
        })
    )

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Ingrese su contraseña"
        })
    )


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombres",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Sus nombres"})
    )
    last_name = forms.CharField(
        label="Apellidos",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Sus apellidos"})
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "ejemplo@correo.com"})
    )
    celular = forms.CharField(
        label="Celular / WhatsApp",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: +57 300..."})
    )
    pais = forms.CharField(
        label="País",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Colombia"})
    )
    ciudad = forms.CharField(
        label="Ciudad",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Bogotá"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("first_name", "last_name", "email")
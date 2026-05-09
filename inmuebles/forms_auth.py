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
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={"placeholder": "Usuario único"})
    )
    first_name = forms.CharField(
        label="Nombres",
        widget=forms.TextInput(attrs={"placeholder": "Sus nombres"})
    )
    last_name = forms.CharField(
        label="Apellidos",
        widget=forms.TextInput(attrs={"placeholder": "Sus apellidos"})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 8 caracteres", "class": "has-icon"}),
        help_text="La contraseña debe tener al menos 8 caracteres."
    )
    password2 = forms.CharField(
        label="Repetir Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Repetí tu contraseña", "class": "has-icon"})
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"placeholder": "ejemplo@correo.com"})
    )
    celular = forms.CharField(
        label="Celular / WhatsApp",
        widget=forms.TextInput(attrs={"placeholder": "Ej: +57 300..."})
    )
    ciudad = forms.CharField(
        label="Ciudad",
        widget=forms.TextInput(attrs={"placeholder": "Ej: Bogotá"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")
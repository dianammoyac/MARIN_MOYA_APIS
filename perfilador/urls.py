from django.urls import path
from .views import inicio

app_name = 'perfilador'
urlpatterns = [path('', inicio, name='inicio')]

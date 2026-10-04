from django.urls import path
from . import views
from . import views_publicas

urlpatterns = [
    path('catalogo/', views.catalogo),
    path('ubicaciones/', views.ubicaciones),
    path('preguntas/', views.preguntas),
    path('cambio/', views.cambio),
    path('referencias/', views.referencias),
    path('perfilaciones/', views.crear),
    path('perfilaciones/<uuid:identificador>/', views.perfil),
    path('perfilaciones/<uuid:identificador>/respuestas/', views.respuestas),
    path('perfilaciones/<uuid:identificador>/evaluar/', views.evaluar),
    path('perfilaciones/<uuid:identificador>/simular/', views.simular),
    path('perfilaciones/<uuid:identificador>/solicitudes/', views.solicitar),
    path('perfilaciones/<uuid:identificador>/evaluaciones/<uuid:registro>/', views.historial_evaluacion),
    path('perfilaciones/<uuid:identificador>/simulaciones/<uuid:registro>/', views.historial_simulacion),
    path('respuestas/', views_publicas.guardar_respuesta),
    path('evaluar/', views_publicas.evaluar),
    path('simular/', views_publicas.simular),
    path('solicitudes/', views_publicas.solicitar),
]

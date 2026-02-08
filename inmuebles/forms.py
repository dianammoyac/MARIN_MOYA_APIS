from django import forms
from .models import Inmueble

class InmuebleForm(forms.ModelForm):
    class Meta:
        model = Inmueble
        # Ajusta esta lista a los campos que realmente tenga tu modelo
        fields = [
            "codigo", "titulo", "descripcion", "tipo", "operacion", "estado",
            "pais", "departamento", "ciudad", "barrio", "direccion",
            "area_m2", "area_construida_m2", "habitaciones", "banos", "parqueaderos",
            "estrato", "piso", "ano_construccion",
            "precio", "administracion", "moneda", "estatus", "destacado",
            "nombre_contacto", "telefono_contacto", "email_contacto",
            "fecha_publicacion", "fecha_actualizacion",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "fecha_publicacion": forms.DateInput(attrs={"type": "date"}),
            "fecha_actualizacion": forms.DateInput(attrs={"type": "date"}),
        }

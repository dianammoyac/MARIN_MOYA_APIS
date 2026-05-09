from django import forms
from .models import Inmueble

class InmuebleForm(forms.ModelForm):
    class Meta:
        model = Inmueble
        # Ajusta esta lista a los campos que realmente tenga tu modelo
        fields = [
        "titulo", "descripcion", "tipo", "operacion", "estado",
        "pais", "departamento", "ciudad", "barrio", "direccion",
        "area_m2", "area_construida_m2", "habitaciones", "banos", "parqueaderos",
        "estrato", "piso", "ano_construccion",
        "precio", "administracion", "moneda", "destacado",
        "nombre_contacto", "telefono_contacto", "email_contacto", 
        "imagen1", "imagen2", "imagen3", "imagen4",
]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

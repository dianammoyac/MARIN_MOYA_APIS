from django import forms
from .models import Inmueble

class InmuebleForm(forms.ModelForm):
    class Meta:
        model = Inmueble
        # La modalidad se deriva del estado físico: EN_CONSTRUCCION es sobre planos,
        # NUEVO/USADO son entrega terminada. Un "nuevo sobre planos" se publica como CESIÓN.
        fields = [
        "titulo", "descripcion", "tipo", "operacion", "estado",
        "meses_entrega", "fecha_entrega_constructora",
        "porcentaje_inicial_exigido", "valor_separacion", "empresa",
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

    def clean(self):
        datos = super().clean()
        estado = datos.get('estado')
        if estado == 'EN_CONSTRUCCION':
            self.instance.modalidad_entrega = 'SOBRE_PLANOS'
        elif estado in ('NUEVO', 'USADO'):
            self.instance.modalidad_entrega = 'TERMINADO'
            for campo in ('meses_entrega', 'porcentaje_inicial_exigido', 'valor_separacion'):
                datos[campo] = None
        return datos

from django.db import migrations


def en_construccion_a_sobre_planos(apps, editor):
    Inmueble = apps.get_model('inmuebles', 'Inmueble')
    Inmueble.objects.filter(estado='EN_CONSTRUCCION').update(modalidad_entrega='SOBRE_PLANOS')


def revertir_a_terminado(apps, editor):
    Inmueble = apps.get_model('inmuebles', 'Inmueble')
    Inmueble.objects.filter(estado='EN_CONSTRUCCION').update(modalidad_entrega='TERMINADO')


class Migration(migrations.Migration):

    dependencies = [
        ('inmuebles', '0006_inmueble_meses_entrega_inmueble_modalidad_entrega'),
    ]

    operations = [
        migrations.RunPython(en_construccion_a_sobre_planos, revertir_a_terminado),
    ]

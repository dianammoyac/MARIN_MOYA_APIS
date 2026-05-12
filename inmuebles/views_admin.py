from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from .models import Inmueble
from django.db.models import Count
from django.contrib import messages

# Solo permite el acceso si es superusuario y el username es 'dianamoya'
@user_passes_test(lambda u: u.is_superuser and u.username == 'dianamoya')
def admin_dashboard(request):
    # KPIs
    usuarios = User.objects.all().order_by('-date_joined')
    inmuebles = Inmueble.objects.all().order_by('-fecha_actualizacion')
    
    total_usuarios = usuarios.count()
    total_activos = inmuebles.filter(estatus='DISPONIBLE').count()
    total_vendidos = inmuebles.filter(estatus='VENDIDO').count()
    total_pendientes = inmuebles.filter(estatus='INACTIVO').count()

    # Datos para Reportes (Distribución por tipo)
    distribucion_tipo = Inmueble.objects.values('tipo').annotate(total=Count('tipo'))
    distribucion_ciudad = Inmueble.objects.values('ciudad').annotate(total=Count('ciudad'))

    # Actividad Reciente (Combinando info de inmuebles y usuarios)
    actividad = inmuebles[:5]

    context = {
        'total_usuarios': total_usuarios,
        'total_activos': total_activos,
        'total_vendidos': total_vendidos,
        'total_pendientes': total_pendientes,
        'usuarios': usuarios,
        'inmuebles': inmuebles,
        'dist_tipo': distribucion_tipo,
        'dist_ciudad': distribucion_ciudad,
        'actividad': actividad,
        'admin_user': request.user,
    }
    
    return render(request, 'inmuebles/admin_panel.html', context)

@user_passes_test(lambda u: u.is_superuser and u.username == 'dianamoya')
def update_user_role(request, user_id):
    if request.method == "POST":
        usuario_obj = get_object_or_404(User, id=user_id)
        role = request.POST.get('role')

        # Protección para la superadministradora principal
        if usuario_obj.username == 'dianamoya':
            messages.error(request, "No se puede modificar el rol del administrador principal.")
            return redirect('admin_dashboard')

        if role == 'admin':
            usuario_obj.is_superuser = True
            usuario_obj.is_staff = True
        elif role == 'agente':
            usuario_obj.is_superuser = False
            usuario_obj.is_staff = True
        else: # usuario
            usuario_obj.is_superuser = False
            usuario_obj.is_staff = False
        
        usuario_obj.save()
        messages.success(request, f"Se ha actualizado el rol de {usuario_obj.username} a {role.upper()}.")
    
    return redirect('admin_dashboard')
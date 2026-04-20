# AGENTS.md - Instrucciones para Agentes de IA

## Proyecto MARÍN MOYA APIS

Portal inmobiliario Django para gestión de propiedades en Colombia. API REST + interfaz web en español.

### Arquitectura Principal
- **Modelo único**: `Inmueble` con 30+ campos (tipo, operación, precio, ubicación, etc.)
- **Vista dual**: API REST (ViewSet) + templates HTML
- **Idioma**: Español completo (etiquetas, forms, chatbot)
- **Base de datos**: MySQL (bd_marinmoya_inversiones)

### Convenciones del Código
- **Nombres en español**: Variables, funciones, clases (ej: `tipo_inmueble`, `precio_venta`)
- **Códigos únicos**: Formato `MM-BOG-0001` (MM-Ciudad-XXXX)
- **Choices fijos**: Para tipo, operación, estado (ver `models.py`)
- **Forms**: ModelForm con Bootstrap (`.form-control`)
- **URLs**: `/inmuebles/` para web, `/api/inmuebles/` para API

### Comandos Esenciales
```bash
python manage.py runserver          # Servidor desarrollo
python manage.py migrate            # Aplicar migraciones BD
python manage.py createsuperuser    # Crear admin
python manage.py test               # Ejecutar tests
```

### Áreas Críticas (Prioridad Alta)
- **Seguridad**: `DEBUG=True`, `SECRET_KEY` hardcoded → mover a variables entorno
- **BD**: Sin contraseña → agregar credenciales seguras
- **Admin**: No configurado → registrar modelo `Inmueble`
- **Tests**: Vacío → crear tests para modelos/vistas

### Patrones Comunes
- **Agregar campo**: models.py → makemigrations → migrate → auto-actualiza forms/serializers
- **Búsqueda**: Usar `Q()` filters en views + input `?q=` en templates
- **Paginación**: `Paginator()` en views + loop en templates
- **Filtros Admin**: `list_filter`, `search_fields` en `@admin.register()`

### Documentación Relacionada
- [Resumen Ejecutivo](memories/repo/RESUMEN_EJECUTIVO_ES.md) - Guía completa del proyecto
- [Patrones y Ejemplos](memories/repo/PATTERNS_Y_EJEMPLOS.md) - 15 patrones con código
- [Arquitectura Técnica](memories/repo/MARIN_MOYA_project_architecture.md) - Detalles técnicos

### Reglas para Agentes IA
- Mantener **idioma español** en todo el código nuevo
- Seguir **convenciones existentes** (nombres, formatos)
- **Priorizar seguridad** en cualquier cambio
- **Probar cambios** con `manage.py test` antes de commit
- **Documentar** cambios significativos en español</content>
<parameter name="filePath">c:\Users\Diana Moya\Desktop\Sena\MARIN_MOYA_APIS\AGENTS.md
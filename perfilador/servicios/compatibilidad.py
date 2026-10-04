from decimal import Decimal
from .preguntas import valor
from .moneda import a_cop
from .ubicaciones import coincide_ubicacion

PESOS = {'presupuesto': 25, 'entrega': 20, 'habitaciones': 10, 'area_m2': 10,
         'ciudad': 25, 'parqueadero': 10}
PESOS_INVERSION = {'presupuesto': 25, 'entrega': 20, 'area_m2': 10,
                   'ciudad': 15, 'objetivo_inversion': 10, 'parqueadero': 5, 'prioridad_inversion': 15}
PESOS_AMBAS = {'presupuesto': 25, 'entrega': 20, 'habitaciones': 8, 'area_m2': 10,
               'ciudad': 15, 'objetivo_inversion': 10, 'parqueadero': 7, 'prioridad_inversion': 5}


def criterio(clave, preferencia, inmueble, cambio=None, respuestas=None):
    """Devuelve puntuación [0,1], razón y datos; None indica dato no verificable."""
    if clave == 'presupuesto':
        if inmueble.moneda not in ('COP', 'USD') or inmueble.precio is None or inmueble.precio <= 0:
            return None, 'Precio comparable en COP pendiente', None
        presupuesto = preferencia if isinstance(preferencia, dict) else {'monto': preferencia, 'moneda': 'COP'}
        maximo = a_cop(presupuesto['monto'], presupuesto['moneda'], cambio)
        precio = a_cop(inmueble.precio, inmueble.moneda, cambio)
        if maximo is None and precio is None and presupuesto['moneda'] == inmueble.moneda == 'USD':
            maximo, precio = Decimal(str(presupuesto['monto'])), inmueble.precio
            moneda_comparacion = 'USD'
        else:
            moneda_comparacion = 'COP'
        if maximo is None or precio is None:
            return None, 'Se requiere una referencia COP/USD vigente para comparar precio y presupuesto', None
        puntuacion = Decimal('1') if precio <= maximo else (maximo / precio if precio else Decimal('0'))
        return puntuacion, 'Precio dentro del presupuesto' if precio <= maximo else 'Precio superior al presupuesto', {'precio': str(precio), 'presupuesto': str(maximo), 'moneda': moneda_comparacion}
    if clave == 'habitaciones':
        real, objetivo = inmueble.habitaciones, int(Decimal(str(preferencia)))
        if real is None:
            return None, 'Habitaciones por confirmar', None
        return min(Decimal('1'), Decimal(real) / max(1, objetivo)), 'Habitaciones suficientes' if real >= objetivo else 'Menos habitaciones de las buscadas', {'habitaciones': real, 'buscadas': objetivo}
    if clave == 'area_m2':
        real, objetivo = inmueble.area_m2, Decimal(str(preferencia))
        if real is None or real <= 0:
            return None, 'Área por confirmar', None
        return min(Decimal('1'), real / max(Decimal('1'), objetivo)), 'Área suficiente' if real >= objetivo else 'Área inferior a la buscada', {'area_m2': str(real), 'buscada': str(objetivo)}
    if clave == 'ciudad':
        lugar = preferencia if isinstance(preferencia, dict) else {'departamento': '', 'ciudad': preferencia}
        ciudad, dep = lugar.get('ciudad', ''), lugar.get('departamento', '')
        if ciudad:
            coincide = coincide_ubicacion(inmueble, dep, ciudad) if dep else inmueble.ciudad.strip().casefold() == ciudad.strip().casefold()
            return Decimal(int(coincide)), 'Ciudad deseada' if coincide else 'Ciudad diferente', {'departamento': inmueble.departamento, 'ciudad': inmueble.ciudad}
        coincide = coincide_ubicacion(inmueble, dep, ciudad)
        return Decimal(int(coincide)), 'Departamento deseado; ciudad flexible' if coincide else 'Departamento diferente', {'departamento': inmueble.departamento}
    if clave == 'parqueadero':
        if preferencia == 'NO':
            return Decimal('1'), 'No requiere parqueadero', {'parqueaderos': inmueble.parqueaderos}
        if inmueble.parqueaderos is None:
            return None, 'Parqueadero por confirmar', None
        coincide = inmueble.parqueaderos > 0
        return Decimal(int(coincide)), 'Tiene parqueadero registrado (inclusión por confirmar)' if coincide else 'No tiene parqueadero registrado', {'parqueaderos': inmueble.parqueaderos}
    if clave == 'entrega':
        deseo = int(Decimal(str(preferencia)))
        modalidad = getattr(inmueble, 'modalidad_entrega', 'TERMINADO') or 'TERMINADO'
        meses = getattr(inmueble, 'meses_entrega', None)
        datos = {'modalidad': modalidad, 'meses_entrega': meses, 'deseo_meses': deseo}
        if modalidad == 'SOBRE_PLANOS' and meses is None:
            return None, 'Meses de entrega por confirmar con la constructora', None
        reales = int(meses or 0)
        if deseo == 0:
            return Decimal('1'), 'Entrega inmediata disponible', datos
        if reales <= deseo:
            razon = 'Entrega inmediata disponible' if reales == 0 else f'Entrega declarada en {reales} meses, dentro del plazo deseado'
            return Decimal('1'), razon, datos
        return (Decimal(deseo) / Decimal(reales)), f'Entrega declarada en {reales} meses, posterior al plazo deseado de {deseo}', datos
    if clave == 'prioridad_inversion':
        mapa = {'MENOR_INVERSION': 'presupuesto', 'UBICACION': 'ciudad', 'ESPACIO': 'area_m2'}
        base = mapa.get(preferencia)
        if base and respuestas and valor(respuestas, base) is not None:
            puntuacion, razon, datos = criterio(base, valor(respuestas, base), inmueble, cambio, respuestas)
            return puntuacion, f'Prioridad de inversión: {razon}', datos
        return None, 'Se necesita un dato comprobable para evaluar esa prioridad de inversión', None
    if clave == 'objetivo_inversion':
        if preferencia == 'RENTA_CORTA':
            return None, 'Renta corta tipo Airbnb: alquiler por días en plataformas; requiere verificar reglamento y autorización, no se afirma por el solo propósito', None
        return None, 'Información comercial pendiente para comparar', None
    # La aptitud de inversión no es verificable con datos del inmueble.
    return None, 'Información comercial pendiente para comparar', None


def evaluar_inmueble(respuestas, inmueble, cambio=None):
    razones, pendientes, excluyentes = [], [], []
    puntos = Decimal('0')
    total = 0
    proposito = valor(respuestas, 'proposito')
    pesos = PESOS_INVERSION if proposito == 'INVERTIR' else PESOS_AMBAS if proposito == 'AMBAS' else PESOS
    deseo_entrega = valor(respuestas, 'entrega')
    if deseo_entrega is not None and int(Decimal(str(deseo_entrega))) == 0:
        modalidad = getattr(inmueble, 'modalidad_entrega', 'TERMINADO') or 'TERMINADO'
        if modalidad == 'SOBRE_PLANOS':
            return {'afinidad': None, 'peso_evaluable': 0, 'razones': [], 'pendientes': [],
                    'exclusiones': ['entrega: requiere entrega inmediata; inmueble sobre planos']}
    for clave, peso in pesos.items():
        preferencia = valor(respuestas, clave)
        inferencia_hogar = False
        if clave == 'habitaciones' and preferencia is None and respuestas.get('habitaciones', {}).get('estado') == 'NO_SE':
            familia = valor(respuestas, 'familia')
            if familia:
                integrantes = sum(familia.values())
                preferencia = str((integrantes + 1) // 2)
                inferencia_hogar = True
        if preferencia is None:
            continue
        puntuacion, razon, datos = criterio(clave, preferencia, inmueble, cambio, respuestas)
        if puntuacion is None:
            pendientes.append(f'{clave}: {razon}')
            continue
        if respuestas[clave].get('indispensable') and puntuacion < 1:
            excluyentes.append(f'{clave}: {razon}')
        total += peso
        puntos += peso * puntuacion
        razones.append({'criterio': clave, 'puntuacion': float(puntuacion),
                        'razon': f'Orientación de habitaciones según integrantes del hogar (1 por cada 2 personas): {razon}' if inferencia_hogar else razon,
                        'datos': datos, 'orientativo': inferencia_hogar})
    for clave in {'ciudad', 'habitaciones', 'area_m2', 'parqueadero', 'presupuesto'} - pesos.keys():
        dato = respuestas.get(clave, {})
        if dato.get('indispensable') and valor(respuestas, clave) is not None:
            puntuacion, razon, _ = criterio(clave, valor(respuestas, clave), inmueble, cambio, respuestas)
            if puntuacion is None:
                pendientes.append(f'{clave}: {razon} (requisito indispensable por confirmar)')
            elif puntuacion < 1:
                excluyentes.append(f'{clave}: {razon}')
    return {
        'afinidad': round(float(100 * puntos / total)) if total else None,
        'peso_evaluable': total, 'razones': razones, 'pendientes': pendientes,
        'exclusiones': excluyentes,
    }

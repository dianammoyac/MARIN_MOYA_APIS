import json
import unicodedata
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def obtener_ubicaciones():
    """Lista territorial local: no depende del inventario ni de una API externa."""
    ruta = Path(__file__).resolve().parents[1] / 'datos' / 'municipios.json'
    with ruta.open(encoding='utf-8') as archivo:
        datos = json.load(archivo)
    return {departamento: sorted(set(ciudades), key=lambda ciudad: ciudad.casefold())
            for departamento, ciudades in sorted(datos.items(), key=lambda item: item[0].casefold())}


def coincide_nombre(actual, deseado):
    def sin_tildes(texto):
        return ''.join(caracter for caracter in unicodedata.normalize('NFD', texto or '')
                       if unicodedata.category(caracter) != 'Mn').strip().casefold()
    return sin_tildes(actual) == sin_tildes(deseado)


def coincide_ubicacion(inmueble, departamento, ciudad):
    if ciudad and not coincide_nombre(inmueble.ciudad, ciudad):
        return False
    if departamento == 'Bogotá D.C.':
        return (coincide_nombre(inmueble.ciudad, 'Bogotá')
                and (coincide_nombre(inmueble.departamento, 'Cundinamarca')
                     or coincide_nombre(inmueble.departamento, 'Bogotá D.C.')))
    return coincide_nombre(inmueble.departamento, departamento)

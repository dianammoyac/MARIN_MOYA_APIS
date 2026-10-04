from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from perfilador.models import ReferenciaCambio


def obtener_cambio_vigente():
    hoy = timezone.localdate()
    return ReferenciaCambio.objects.filter(activa=True, fecha__lte=hoy, fecha__gte=hoy - timedelta(days=7)).order_by('-fecha', '-pk').first()


def a_cop(monto, moneda, cambio):
    if monto is None:
        return None
    if moneda == 'COP':
        return Decimal(str(monto))
    if moneda == 'USD' and cambio:
        return Decimal(str(monto)) * cambio.cop_por_usd
    return None

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from perfilador.models import Perfilacion


class Command(BaseCommand):
    help = 'Previsualiza o elimina perfilaciones anónimas abandonadas sin solicitudes de asesoría.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=90)
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, **opciones):
        dias = opciones['dias']
        if dias < 1:
            raise CommandError('dias debe ser mayor que cero.')
        limite = timezone.now() - timedelta(days=dias)
        candidatas = Perfilacion.objects.filter(usuario__isnull=True, actualizado__lt=limite, solicitudes__isnull=True)
        cantidad = candidatas.count()
        if opciones['aplicar']:
            candidatas.delete()
        self.stdout.write(f'{cantidad} perfilaciones anónimas sin solicitud {"eliminadas" if opciones["aplicar"] else "elegibles; sin cambios"}.')

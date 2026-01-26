from rest_framework import serializers
from .models import Inmueble


class InmuebleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inmueble
        fields = '__all__'

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0.")
        return value

    def validate_area_m2(self, value):
        if value <= 0:
            raise serializers.ValidationError("El área (m2) debe ser mayor a 0.")
        return value

    def validate_estrato(self, value):
        if value is not None and (value < 1 or value > 6):
            raise serializers.ValidationError("El estrato debe estar entre 1 y 6.")
        return value

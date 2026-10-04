# Usamos una imagen estable de Python
FROM python:3.12-slim

# Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requerimientos.txt /app/
RUN pip install --no-cache-dir -r requerimientos.txt

COPY . /app/

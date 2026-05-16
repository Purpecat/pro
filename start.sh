#!/bin/bash
echo "=== Установка системных зависимостей ==="
apt-get update
apt-get install -y spatialindex libspatialindex-dev

echo "=== Содержимое директории ==="
ls -la
ls -la graphs/ || echo "Папка graphs не найдена"

echo "=== Запуск приложения ==="
gunicorn --timeout 120 --workers 1 app:app

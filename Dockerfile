# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для rtree и гео-библиотек
RUN apt-get update && apt-get install -y \
    libspatialindex-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Hugging Face Spaces ожидает приложение на порту 7860
ENV PORT=7860

# Команда запуска
CMD ["gunicorn", "app.app:app", "--bind", "0.0.0.0:7860", "--timeout", "120"]

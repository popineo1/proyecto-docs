FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para PostgreSQL y procesamiento
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary supabase gunicorn uvicorn

# Copiar el resto del código
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para arrancar en producción (usando la variable PORT de Render)
CMD ["sh", "-c", "gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}"]

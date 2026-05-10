FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
# (Asegúrate de tener un archivo requirements.txt en la raíz)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente y carpetas necesarias
COPY src/ ./src/
COPY logs/ ./logs/

# Variables de entorno para que el contenedor sepa dónde están las bases de datos
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV REDIS_HOST=redis
ENV POSTGRES_HOST=postgres

# Comando por defecto: inicia el productor de Kafka
CMD ["python", "src/ingesta/kafka_producer.py"]
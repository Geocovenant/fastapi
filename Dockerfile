FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias de sistema para psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego, si tienes un archivo de dependencias bloqueadas:
# COPY requirements-lock.txt .
# RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

# Port exposed by the application
EXPOSE 8080

# Command to execute the application
CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8080"]
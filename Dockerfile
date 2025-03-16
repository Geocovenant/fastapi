FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Command to execute the application
CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8080"]
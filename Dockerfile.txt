FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Poetry
RUN pip install --no-cache-dir poetry

# Bağımlılıkları önbellekleyebilmek için önce manifestleri kopyala
COPY pyproject.toml poetry.lock* ./

# Sanal ortam oluşturma yerine sistem içine kur
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-root

# Uygulama kodu
COPY . .

EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

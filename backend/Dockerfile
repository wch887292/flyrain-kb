FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=fhzsk.settings.prod

WORKDIR /app

# 系统依赖（pgvector 客户端、PDF解析可选）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install .

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn fhzsk.wsgi:application -b 0.0.0.0:8000 --workers 2"]

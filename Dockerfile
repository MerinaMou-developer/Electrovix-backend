# Dockerfile

FROM python:3.11-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .



# Expose port
EXPOSE 8000

# Run migrations, collect static, create superuser (if env vars set), seed products, then start server
# Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD in Render env
CMD bash -c "python manage.py migrate && python manage.py collectstatic --noinput && python manage.py createsuperuser --noinput 2>/dev/null || true && python manage.py seed_products && gunicorn backend.wsgi:application --bind 0.0.0.0:8000"

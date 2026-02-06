# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV UV_SYSTEM_PYTHON=1

# Set work directory
WORKDIR /app

# Install system dependencies
# libpango* and libpq-dev are for WeasyPrint and Psycopg2 respectively
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies using uv
COPY requirements.txt /app/
RUN uv pip install -r requirements.txt

# Copy project files
COPY . /app/

# Expose ports (although only one is used per container, this documents intent)
EXPOSE 5000
EXPOSE 8501

# Default command (can be overridden)
CMD ["python3", "--version"]

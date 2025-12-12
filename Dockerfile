FROM python:3.13.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for OpenCASCADE/CadQuery
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY enginel/requirements.txt .
RUN uv pip install -r requirements.txt --system

COPY enginel/ .

EXPOSE 8000

CMD ["./entrypoint.sh"]
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
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY enginel/requirements.txt .
RUN uv pip install -r requirements.txt --system

# Create non-root user for security with home directory
RUN groupadd -r enginel --gid=1000 && \
    useradd -r -g enginel --uid=1000 --create-home enginel

COPY enginel/ .

# Change ownership of application files and ensure cache directory exists
# Also make entrypoint.sh executable
RUN chown -R enginel:enginel /app && \
    mkdir -p /home/enginel/.cache && \
    chown -R enginel:enginel /home/enginel/.cache && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER enginel

EXPOSE 8000

CMD ["./entrypoint.sh"]
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgeos-dev \
    libgdal-dev \
    gdal-bin \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy package specifications
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies first (layer-cached)
RUN uv pip install -r pyproject.toml

# Copy source code and ML models/inference
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY migrations/ ./migrations/
COPY alembic.ini ./

RUN uv pip install --no-deps -e "."

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

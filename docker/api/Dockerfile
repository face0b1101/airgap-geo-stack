FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency manifests and metadata files hatchling needs
COPY pyproject.toml uv.lock LICENSE README.md ./

# Install production dependencies only (no dev group)
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "airgap_geo_api.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "5000"]

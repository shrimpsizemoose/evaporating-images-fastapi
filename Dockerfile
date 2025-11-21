FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/shrimpsizemoose/evaporating-images-fastapi
LABEL org.opencontainers.image.description="Real-time pixel art animation system with evaporating pixels"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY app ./app
COPY static ./static
COPY figures ./figures

ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

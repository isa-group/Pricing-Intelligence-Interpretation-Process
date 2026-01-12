# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ARG HARVEY_STATIC_DIR
RUN mkdir -p $HARVEY_STATIC_DIR

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"
ENV UV_SYSTEM_PYTHON=true

# Copy H.A.R.V.E.Y. API sources
COPY harvey_api/pyproject.toml harvey_api/uv.lock .
COPY harvey_api/src ./src
RUN uv sync --frozen --no-install-project

EXPOSE 8086

CMD ["uvicorn", "src.harvey_api.app:app", "--host", "0.0.0.0", "--port", "8086"]

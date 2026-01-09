# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# Copy H.A.R.V.E.Y. API sources
COPY harvey_api/pyproject.toml ./pyproject.toml
COPY harvey_api/README.md ./README.md
COPY harvey_api/src ./src

# Install H.A.R.V.E.Y. API
RUN uv pip install --system .

EXPOSE 8086

CMD ["uvicorn", "harvey_api.app:app", "--host", "0.0.0.0", "--port", "8086"]

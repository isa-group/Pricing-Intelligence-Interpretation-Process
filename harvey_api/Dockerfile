FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ARG HARVEY_STATIC_DIR=/app/static
ENV HARVEY_STATIC_DIR=${HARVEY_STATIC_DIR}

RUN mkdir -p "${HARVEY_STATIC_DIR}"

WORKDIR /app

# Copy H.A.R.V.E.Y. API sources
COPY harvey_api/pyproject.toml harvey_api/uv.lock .
COPY harvey_api/src ./src
RUN uv sync --frozen --no-install-project

EXPOSE 8086

CMD ["uv", "run", "uvicorn", "src.harvey_api.app:app", "--host", "0.0.0.0", "--port", "8086"]

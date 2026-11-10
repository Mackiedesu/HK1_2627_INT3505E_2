# ─── stage 1: builder ───
FROM python:3.12-slim AS builder
WORKDIR /build

COPY pyproject.toml ./
COPY src ./src

# Create virtual environment and install package dependencies without cache
RUN pip install --no-cache-dir uv \
    && uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH
RUN uv pip install --no-cache .

# ─── stage 2: runtime ───
FROM python:3.12-slim
WORKDIR /app

# Create non-root system user and group for security
RUN groupadd -r app && \
    useradd -r -g app -d /app app

# Copy pre-built virtual environment from builder stage
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app wsgi.py gunicorn.conf.py ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app openapi ./openapi

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "product_api.factory:create_app()"]

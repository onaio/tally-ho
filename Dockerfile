# syntax=docker/dockerfile:1

# Stage 1: Build — resolve deps into a production venv at /opt/venv and collect
# static assets. The venv lives outside the project dir so a dev-time bind mount
# of the source (docker-compose) won't clobber it.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /code

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-cache --no-dev

COPY . /code
RUN uv run python manage.py collectstatic --no-input

# Stage 2: Runtime — slim image, no uv, no build tools
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /code

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /code/tally_ho/static /code/tally_ho/static
COPY . /code

EXPOSE 8000

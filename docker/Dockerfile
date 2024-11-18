# syntax=docker/dockerfile:1.4
ARG PYTHON_IMAGE=ghcr.io/astral-sh/uv:python3.12-bookworm-slim

FROM $PYTHON_IMAGE as build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git

ENV UV_LINK_MODE=copy
ENV PATH=/root/.local/bin:/app/.venv/bin:$PATH

RUN --mount=type=cache,target=/root/.cache/uv \
    uv tool install codecov-cli

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["uv", "run", "bash"]
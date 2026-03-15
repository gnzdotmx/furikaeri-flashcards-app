FROM node:20-alpine@sha256:b88333c42c23fbd91596ebd7fd10de239cedab9617de04142dde7315e3bc0afa AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json /web/
RUN npm ci
COPY web/index.html /web/index.html
COPY web/vite.config.ts /web/vite.config.ts
COPY web/vitest.config.ts /web/vitest.config.ts
COPY web/tsconfig.json /web/tsconfig.json
COPY web/tsconfig.node.json /web/tsconfig.node.json
COPY web/eslint.config.js /web/eslint.config.js
COPY web/src /web/src
RUN npm run build

FROM python:3.12-slim@sha256:ccc7089399c8bb65dd1fb3ed6d55efa538a3f5e7fca3f5988ac3b5b87e593bf0 AS api
# Pin uv version for reproducible builds (https://docs.astral.sh/uv/guides/integration/docker/)
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN useradd -m -u 10001 appuser
RUN mkdir -p /data && chown -R appuser:appuser /data
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (better layer caching). Include dev group for make test/lint.
COPY api/pyproject.toml api/uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable --extra dev

# Copy app and scripts, then install project
COPY api/app /app/app
COPY api/scripts /app/scripts
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --extra dev

# Copy built web assets into API for production serving
COPY --from=web-build /web/dist /app/app/static

RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH" \
    SERVE_WEB=true
CMD ["sh", "-c", "uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}"]

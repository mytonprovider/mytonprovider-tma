FROM node:24-alpine AS frontend
WORKDIR /build
ARG VITE_TG_CLIENT_ID
ENV VITE_TG_CLIENT_ID=$VITE_TG_CLIENT_ID
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend .
RUN pnpm build

FROM python:3.12-slim
WORKDIR /backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY --from=frontend /build/dist backend/static
COPY --chmod=755 entrypoint.sh .
CMD ["./entrypoint.sh"]

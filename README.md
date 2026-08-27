# 💎 My TON Provider

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Telegram Mini App](https://img.shields.io/badge/Telegram-Mini%20App-blue?logo=telegram&logoColor=white)](https://core.telegram.org/bots/webapps)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-teal?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-blue?logo=react&logoColor=white)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-blue?logo=docker&logoColor=white)](https://www.docker.com/)

![My TON Provider](app/frontend/public/banner.png)

**My TON Provider** is a Telegram Mini App for monitoring TON storage providers, in Telegram or the browser:
provider catalog with search, sorting and filters; status, telemetry, hardware and network details; alerts on
downtime, overload and restarts; favorites, theme and language synced to the account; owner metrics, earnings,
balance and charts once ownership is verified.

## Usage

1. Copy the environment file and fill it in (see [Environment Variables](#environment-variables)):

   ```bash
   cp .env.example .env
   ```

2. Build and start with Docker Compose:

   ```bash
   docker compose up --build
   ```

The frontend is compiled into the backend's static directory, migrations run, and the service starts on `:8080`.

### Local development

Backend:

```bash
cd app/backend
alembic upgrade head
python -m app
```

Frontend:

```bash
cd app/frontend
pnpm install
pnpm dev
```

The dev server proxies `/api` to `$BACKEND`, `http://localhost:8080` by default, so the frontend can run against a
local backend or a deployed one (`BACKEND=https://example.org pnpm dev`, or the same line in `app/frontend/.env.local`).
Outside Telegram the app authenticates through the Telegram Login Widget, which only works on the domain registered
with the bot.

## Environment Variables

| Variable                | Description                                                            | Example                   |
|-------------------------|------------------------------------------------------------------------|---------------------------|
| `LOG_LEVEL`             | Level for `app.*` loggers: `DEBUG`, `INFO`, `WARNING`, `ERROR`         | `INFO`                    |
| `API_RATE_LIMIT`        | Requests per window per client IP on catalog endpoints (bag, provider) | `100`                     |
| `API_RATE_WINDOW`       | Rate-limit window, in seconds                                          | `60`                      |
| `AUTH_RATE_LIMIT`       | Requests per window per client IP on auth endpoints                    | `30`                      |
| `WEBAPP_URL`            | Public app URL; base for the Telegram bot webhook                      | `https://mtp.example.com` |
| `BOT_TOKEN`             | Bot token from @BotFather                                              | `123456:qweRTY`           |
| `BOT_USERNAME`          | Bot username, without `@`                                              | `mytonproviderbot`        |
| `BOT_WEBHOOK_SECRET`    | Secret guarding the webhook endpoint                                   | `s3cret`                  |
| `BOT_DEV_IDS`           | Telegram user IDs receiving worker error reports; empty disables       | `123,456`                 |
| `BOT_ADMIN_IDS`         | Telegram user IDs granted admin access                                 | `123,456`                 |
| `JWT_SECRET`            | Session-token signing key (≥ 32 bytes)                                 | `a-long-random-string`    |
| `TG_CLIENT_ID`          | Telegram Login Widget client ID (OIDC)                                 | `123456789`               |
| `TG_CLIENT_SECRET`      | Telegram Login Widget client secret                                    | `qweRTY`                  |
| `TONCENTER_API_KEY`     | toncenter API key                                                      | `qweRTY`                  |
| `TONCENTER_API_RPS`     | toncenter rate limit, requests per second                              | `10`                      |
| `MYTONPROVIDER_API_KEY` | mytonprovider API key                                                  | `qweRTY`                  |
| `MYTONPROVIDER_API_RPS` | mytonprovider rate limit, requests per second                          | `10`                      |

The frontend reads three more variables, inlined by Vite at build time rather than read from the runtime `.env`:

| Variable            | Description                                                                      | Default                     |
|---------------------|----------------------------------------------------------------------------------|-----------------------------|
| `VITE_BACKEND_BASE` | This backend's origin; in production one process serves both the app and the API | same origin                 |
| `VITE_API_BASE`     | Public catalog API                                                               | `https://mytonprovider.org` |
| `VITE_TG_CLIENT_ID` | Telegram Login Widget client ID; Docker Compose bakes it from `TG_CLIENT_ID`     | empty                       |

## License

This repository is distributed under the [Apache License 2.0](LICENSE).

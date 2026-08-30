import logging
import sys
from pathlib import Path

from environs import Env

env = Env()
env.read_env()

TIMEZONE = "Europe/Moscow"
BASE_DIR = Path(__file__).resolve().parent.parent
DEV = "--dev" in sys.argv
LOG_LEVEL = env.log_level("LOG_LEVEL", logging.INFO)

APP_REPO = env.str("APP_REPO", "")
APP_BRANCH = env.str("APP_BRANCH", "")
APP_COMMIT = env.str("APP_COMMIT", "")

JWT_SECRET = env.str("JWT_SECRET")
WEBAPP_URL = env.str("WEBAPP_URL").rstrip("/")
API_RATE_LIMIT = env.int("API_RATE_LIMIT", 100)
API_RATE_WINDOW = env.int("API_RATE_WINDOW", 60)
AUTH_RATE_LIMIT = env.int("AUTH_RATE_LIMIT", 30)

TG_CLIENT_ID = env.int("TG_CLIENT_ID")
TG_CLIENT_SECRET = env.str("TG_CLIENT_SECRET")

BOT_TOKEN = env.str("BOT_TOKEN")
BOT_DEV_IDS = env.list("BOT_DEV_IDS", [], subcast=int)
BOT_ADMIN_IDS = env.list("BOT_ADMIN_IDS", [], subcast=int)
BOT_USERNAME = env.str("BOT_USERNAME")
ADMIN_IDS = frozenset(BOT_DEV_IDS + BOT_ADMIN_IDS)
BOT_WEBHOOK_SECRET = env.str("BOT_WEBHOOK_SECRET")
DEV_MASTER_PASS = env.str("DEV_MASTER_PASS", "")

TONCENTER_API_URL = "https://toncenter.com/api/v3"
TONCENTER_API_KEY = env.str("TONCENTER_API_KEY")
TONCENTER_API_RPS = env.float("TONCENTER_API_RPS")

MYTONPROVIDER_API_URL = "https://mytonprovider.org/api/v1"
MYTONPROVIDER_API_KEY = env.str("MYTONPROVIDER_API_KEY")
MYTONPROVIDER_API_RPS = env.float("MYTONPROVIDER_API_RPS")

# The salt is public and dictated by upstream: providers hash their password the
# same way, so this string cannot be changed to something stronger on our side.
TELEMETRY_PASS_SALT = f"{MYTONPROVIDER_API_URL}/providers"

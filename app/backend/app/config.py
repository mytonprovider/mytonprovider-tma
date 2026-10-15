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

# Not "*": that trusts the leftmost X-Forwarded-For, which is whatever the client sent.
TRUSTED_PROXIES = env.str("FORWARDED_ALLOW_IPS", "127.0.0.1,172.16.0.0/12")

TG_CLIENT_ID = env.int("TG_CLIENT_ID")
TG_CLIENT_SECRET = env.str("TG_CLIENT_SECRET")

BOT_TOKEN = env.str("BOT_TOKEN")
BOT_USERNAME = env.str("BOT_USERNAME")
BOT_WEBHOOK_SECRET = env.str("BOT_WEBHOOK_SECRET")

# The rest of the admins are rows in "admins", added by this one in the panel.
ADMIN_ID = env.int("ADMIN_ID")

TONCENTER_API_URL = "https://toncenter.com/api/v3"
TONCENTER_API_KEY = env.str("TONCENTER_API_KEY")
TONCENTER_API_RPS = env.float("TONCENTER_API_RPS")

MYTONPROVIDER_API_URL = "https://mytonprovider.org/api/v1"
MYTONPROVIDER_API_KEY = env.str("MYTONPROVIDER_API_KEY")
MYTONPROVIDER_API_RPS = env.float("MYTONPROVIDER_API_RPS")

# The salt is public and dictated by upstream: providers hash their password the
# same way, so this string cannot be changed to something stronger on our side.
TELEMETRY_PASS_SALT = f"{MYTONPROVIDER_API_URL}/providers"

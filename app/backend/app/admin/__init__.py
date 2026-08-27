from pathlib import Path

from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette_admin.contrib.sqla import Admin

from app import config
from app.admin.auth import TelegramAuthProvider
from app.admin.views import VIEWS, HomeView
from app.api import auth
from app.db import session_factory

admin = Admin(
    session_factory,
    title="Admin Panel",
    favicon_url="/logo.svg",
    templates_dir=str(Path(__file__).parent / "templates"),
    index_view=HomeView(menu_label="Home", icon="fa-solid fa-house", path="/"),
    auth_provider=TelegramAuthProvider(),
    secret_key=config.JWT_SECRET,
    middlewares=[
        Middleware(
            SessionMiddleware,
            secret_key=config.JWT_SECRET,
            path="/admin",
            max_age=int(auth.SESSION_TTL.total_seconds()),
            https_only=not config.DEV,
        )
    ],
)
for view in VIEWS:
    admin.add_view(view)


def mount(app: FastAPI) -> None:
    app.add_route("/admin", lambda _request: RedirectResponse("/admin/"))
    admin.mount_to(app)

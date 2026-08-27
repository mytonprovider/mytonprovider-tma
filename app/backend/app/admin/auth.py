import logging

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.status import (
    HTTP_204_NO_CONTENT,
    HTTP_303_SEE_OTHER,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)
from starlette.templating import Jinja2Templates
from starlette_admin.auth import AdminUser, BaseAuthProvider
from starlette_admin.helpers import index_url

from app import config
from app.api import auth
from app.db import session_factory
from app.db.repos import UserRepo

logger = logging.getLogger(__name__)


class TelegramAuthProvider(BaseAuthProvider):
    templates: Jinja2Templates

    def __init__(self) -> None:
        super().__init__(allow_routes=["csrf", "session"])

    def get_routes(self, templates: Jinja2Templates) -> list[Route]:
        self.templates = templates
        return [
            Route(self.login_path, self.render_login, methods=["GET"], name="login"),
            Route(self.logout_path, self.render_logout, methods=["POST"], name="logout"),
            Route("/csrf", self.issue_csrf, methods=["GET"], name="csrf"),
            Route("/session", self.open_session, methods=["POST"], name="session"),
        ]

    @staticmethod
    async def issue_csrf(request: Request) -> Response:
        return Response(status_code=HTTP_204_NO_CONTENT)

    @staticmethod
    async def open_session(request: Request) -> Response:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse({"detail": "Missing bearer token"}, HTTP_401_UNAUTHORIZED)
        try:
            user_id = auth.read_session_token(token)
        except HTTPException:
            return JSONResponse({"detail": "Invalid session token"}, HTTP_401_UNAUTHORIZED)
        if user_id not in config.ADMIN_IDS:
            logger.warning("access denied for %s", user_id)
            return JSONResponse({"detail": "Access denied"}, HTTP_403_FORBIDDEN)
        async with session_factory() as session:
            user = await UserRepo(session).get(user_id)
        if user is None or user.banned_at is not None:
            logger.warning("access denied for %s", user_id)
            return JSONResponse({"detail": "Access denied"}, HTTP_403_FORBIDDEN)
        request.session["user_id"] = user_id
        request.session["username"] = user.username or user.fullname
        request.session["photo_url"] = user.photo_url
        logger.info("logged in: %s", user_id)
        return Response(status_code=HTTP_204_NO_CONTENT)

    async def render_login(self, request: Request) -> Response:
        if getattr(request.state, "admin_user", None) is not None:
            return RedirectResponse(index_url(request), status_code=HTTP_303_SEE_OTHER)
        return self.templates.TemplateResponse(
            request=request,
            name="no_access.html",
            status_code=HTTP_403_FORBIDDEN,
        )

    @staticmethod
    async def render_logout(request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(index_url(request), status_code=HTTP_303_SEE_OTHER)

    async def authenticate(self, request: Request) -> AdminUser | None:
        user_id = request.session.get("user_id")
        if user_id not in config.ADMIN_IDS:
            return None
        username = request.session.get("username")
        return AdminUser(username=username or str(user_id), photo_url=request.session.get("photo_url"))

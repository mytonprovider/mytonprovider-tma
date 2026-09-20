import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from fastapi.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route
from starlette.status import HTTP_303_SEE_OTHER, HTTP_403_FORBIDDEN
from starlette.templating import Jinja2Templates
from starlette_admin.auth import AdminUser, OAuthProvider
from starlette_admin.helpers import index_url, safe_redirect_url

from app import config
from app.api import auth
from app.db import session_factory
from app.db.models import UserModel
from app.db.repos import SessionRepo

logger = logging.getLogger(__name__)

# Has to match a Redirect URL registered in BotFather byte for byte, so it is built
# from the configured origin and not from proxy headers the way request.url_for does.
REDIRECT_URI = f"{config.WEBAPP_URL}/admin/oauth/callback"
STATE_KEY = "oauth_state"
NEXT_KEY = "oauth_next"
# The signed cookie carries nothing but the OIDC handshake, so it expires with it.
STATE_TTL = timedelta(minutes=10)


class TelegramAuthProvider(OAuthProvider):
    templates: Jinja2Templates

    def get_routes(self, templates: Jinja2Templates) -> list[Route]:
        self.templates = templates
        return super().get_routes(templates)

    async def redirect_to_provider(self, request: Request, _callback_url: str) -> Response:
        state = secrets.token_urlsafe(16)
        request.session[STATE_KEY] = state
        # The redirect URI is fixed, so the page the user asked for travels in the session.
        request.session[NEXT_KEY] = request.query_params.get("next", "")
        params = urlencode(
            {
                "response_type": "code",
                "client_id": str(config.TG_CLIENT_ID),
                "redirect_uri": REDIRECT_URI,
                "scope": "openid profile",
                "state": state,
            }
        )
        return RedirectResponse(f"{auth.OIDC_AUTH_URL}?{params}", status_code=HTTP_303_SEE_OTHER)

    # The base class leaves the callback nothing to answer with, so the opened session
    # travels to render_callback on the request.
    async def handle_callback(self, request: Request) -> None:
        state = request.session.pop(STATE_KEY, None)
        code = request.query_params.get("code")
        if not state or not code or request.query_params.get("state") != state:
            raise auth.unauthorized("Invalid callback")
        id_token = await auth.exchange_code(code, REDIRECT_URI)
        claims = await run_in_threadpool(auth.verify_id_token, id_token)
        async with session_factory() as session:
            user = await auth.user_from_claims(claims, session)
            if user.id not in config.ADMIN_IDS:
                logger.warning("access denied for %s", user.id)
                raise HTTPException(HTTP_403_FORBIDDEN, "Access denied")
            token = await auth.open_session(session, user.id)
            await session.commit()
            request.state.login = (self._admin_user(user), token)
        logger.info("logged in: %s", user.id)

    async def render_callback(self, request: Request) -> Response:
        next_url = request.session.pop(NEXT_KEY, "")
        try:
            await self.handle_callback(request)
        except HTTPException as error:
            logger.warning("login failed: %s", error.detail)
            return self._render_gate(request, denied=True, status_code=HTTP_403_FORBIDDEN)
        admin_user, token = request.state.login
        await self._emit_after_login(request, admin_user)
        fallback = index_url(request)
        target = safe_redirect_url(next_url or fallback, request, fallback)
        response = RedirectResponse(target, status_code=HTTP_303_SEE_OTHER)
        auth.set_session_cookie(response, token)
        return response

    async def logout(self, request: Request) -> Response:
        request.session.clear()
        user = await self._session_user(request)
        if user is not None:
            async with session_factory() as session:
                await SessionRepo(session).close(user.id)
                await session.commit()
        # Redirecting to the index would bounce right back into the provider and log the
        # user in again, so the gate itself is the logged out screen.
        response = self._render_gate(request, denied=False)
        auth.clear_session_cookie(response)
        return response

    def _render_gate(self, request: Request, denied: bool, status_code: int = 200) -> Response:
        return self.templates.TemplateResponse(
            request=request,
            name="no_access.html",
            context={"denied": denied},
            status_code=status_code,
        )

    # The panel rides the session of the app itself: same host, same cookie.
    async def _session_user(self, request: Request) -> UserModel | None:
        token = request.cookies.get(auth.SESSION_COOKIE)
        if token is None:
            return None
        async with session_factory() as session:
            user = await auth.find_session(session, token)
        return user if user is not None and user.id in config.ADMIN_IDS else None

    def _admin_user(self, user: UserModel) -> AdminUser:
        return AdminUser(username=user.username or user.fullname or str(user.id), photo_url=user.photo_url)

    async def authenticate(self, request: Request) -> AdminUser | None:
        user = await self._session_user(request)
        return self._admin_user(user) if user is not None else None

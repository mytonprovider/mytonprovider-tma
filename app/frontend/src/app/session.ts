import { BackendError, backend } from "@/data/backend";
import { getInitDataRaw, getTelegramUser, isInTelegram } from "@/lib/telegram";
import { consumeRedirectCode, redirectUri } from "@/lib/telegramLogin";
import { hydrateFromServer } from "@/data/sync";
import { makeAuthUser, useAuth } from "@/stores/auth";
import { useSubscriptions } from "@/stores/subscriptions";

function tokenUserId(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1])) as { sub?: unknown };
    return Number(payload.sub) || null;
  } catch {
    return null;
  }
}

async function finishRedirectLogin(code: string): Promise<void> {
  const auth = useAuth.getState();
  const result = await backend.authCode(code, redirectUri());
  auth.login(makeAuthUser(result.name ?? "Telegram User", null, result.username, result.photo_url));
  auth.setToken(result.token);
}

export async function establishSession(): Promise<void> {
  const auth = useAuth.getState();
  const code = isInTelegram() ? null : consumeRedirectCode();
  try {
    if (code) {
      await finishRedirectLogin(code);
    } else if (isInTelegram()) {
      const raw = getInitDataRaw();
      if (!raw) return;
      try {
        const { token } = await backend.authTelegram(raw);
        auth.setToken(token);
      } catch (error) {
        if (!(error instanceof BackendError && error.status === 401)) throw error;
        if (!auth.token || tokenUserId(auth.token) !== getTelegramUser()?.id) throw error;
        const { token } = await backend.refresh();
        auth.setToken(token);
      }
    } else if (auth.token) {
      const { token } = await backend.refresh();
      auth.setToken(token);
    } else {
      if (auth.loggedIn) auth.logout();
      return;
    }
    await hydrateFromServer(true);
  } catch (error) {
    if (error instanceof BackendError && error.detail === "Banned") auth.setBanned(true);
    console.error("backend session failed", error);
    if (!isInTelegram() && error instanceof BackendError && error.status === 401) auth.logout();
  }
}

export function endSession(): void {
  const auth = useAuth.getState();
  if (auth.isAdmin) void backend.adminLogout().catch(() => {});
  auth.logout();
  useSubscriptions.getState().setAll([]);
}

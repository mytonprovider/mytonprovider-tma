import { BackendError, backend, openTelegramSession } from "@/data/backend";
import { isInTelegram } from "@/lib/telegram";
import { consumeRedirectCode, redirectUri } from "@/lib/telegramLogin";
import { hydrateFromServer } from "@/data/sync";
import { makeAuthUser, useAuth } from "@/stores/auth";
import { useSubscriptions } from "@/stores/subscriptions";

async function finishRedirectLogin(code: string): Promise<void> {
  const auth = useAuth.getState();
  const result = await backend.authCode(code, redirectUri());
  auth.login(makeAuthUser(result.name ?? "Telegram User", null, result.username, result.photo_url));
}

export async function establishSession(): Promise<void> {
  const auth = useAuth.getState();
  const code = isInTelegram() ? null : consumeRedirectCode();
  try {
    if (code) {
      await finishRedirectLogin(code);
    } else if (isInTelegram()) {
      const token = (await openTelegramSession()) ?? useAuth.getState().token;
      if (!token) {
        auth.closeSession();
        return;
      }
      auth.openSession();
    }
    await hydrateFromServer(true);
    if (!isInTelegram()) auth.openSession();
  } catch (error) {
    if (error instanceof BackendError && error.detail === "Banned") auth.setBanned(true);
    if (error instanceof BackendError && error.status === 401) {
      sessionLost();
      return;
    }
    console.error("backend session failed", error);
  }
}

// Inside Telegram a 401 reaches here only after request() has already retried with a fresh
// token, so the session just closes; the screen offers a retry.
export function sessionLost(): void {
  if (isInTelegram()) {
    useAuth.getState().closeSession();
    return;
  }
  useAuth.getState().logout();
  useSubscriptions.getState().setAll([]);
}

export function endSession(): void {
  void backend.logout().catch((error: unknown) => console.error("logout failed", error));
  useAuth.getState().logout();
  useSubscriptions.getState().setAll([]);
}

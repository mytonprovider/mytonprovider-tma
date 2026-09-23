import { BackendError, backend } from "@/data/backend";
import { getInitDataRaw, isInTelegram } from "@/lib/telegram";
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
      if (!getInitDataRaw()) return;
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

// Inside Telegram the identity comes from the client and there is no way back in from
// the screen, so a refused request only closes the session and waits for fresh init data.
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

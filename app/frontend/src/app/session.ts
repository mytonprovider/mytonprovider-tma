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
  auth.openSession();
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
      const { token } = await backend.authTelegram(raw);
      auth.openSession(token);
    }
    await hydrateFromServer(true);
    if (!isInTelegram()) auth.openSession();
  } catch (error) {
    if (error instanceof BackendError && error.detail === "Banned") auth.setBanned(true);
    if (!isInTelegram() && error instanceof BackendError && error.status === 401) {
      auth.logout();
      return;
    }
    console.error("backend session failed", error);
  }
}

export function endSession(): void {
  void backend.logout().catch((error: unknown) => console.error("logout failed", error));
  useAuth.getState().logout();
  useSubscriptions.getState().setAll([]);
}

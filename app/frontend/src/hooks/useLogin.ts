import { backend } from "@/data/backend";
import { hydrateFromServer } from "@/data/sync";
import { useAppliedLang } from "@/i18n";
import { notify } from "@/lib/telegram";
import { isCoarsePointer, isWidgetConfigured, openTelegramLogin, startRedirectLogin, type WidgetClaims } from "@/lib/telegramLogin";
import { type AuthUser, makeAuthUser, useAuth } from "@/stores/auth";
import { useCallback, useState } from "react";

const MOCK_USER: AuthUser = { name: "TON Provider", username: "provider", initials: "TP", photoUrl: null };

function fromWidgetClaims(claims: WidgetClaims): AuthUser {
  const first = claims.given_name || claims.name || "Telegram User";
  const last = claims.given_name ? claims.family_name : undefined;
  return makeAuthUser(first, last, claims.preferred_username, claims.picture);
}

export function useLogin() {
  const login = useAuth((state) => state.login);
  const lang = useAppliedLang();
  const [pending, setPending] = useState(false);

  const start = useCallback(() => {
    if (pending) return;
    if (!isWidgetConfigured()) {
      if (import.meta.env.DEV) login(MOCK_USER);
      else console.error("Telegram login is not configured: set VITE_TG_CLIENT_ID");
      return;
    }
    if (isCoarsePointer()) {
      startRedirectLogin(lang);
      return;
    }
    setPending(true);
    openTelegramLogin(lang)
      .then(async (auth) => {
        if (!auth) return;
        const { token } = await backend.authWidget(auth.idToken);
        login(fromWidgetClaims(auth.user));
        useAuth.getState().setToken(token);
        await hydrateFromServer(true);
        notify("success");
      })
      .catch((error: unknown) => {
        console.error("Telegram login failed", error);
        notify("error");
      })
      .finally(() => setPending(false));
  }, [pending, login, lang]);

  return { start, pending };
}

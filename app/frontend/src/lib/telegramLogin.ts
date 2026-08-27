const SCRIPT_URL = "https://oauth.telegram.org/js/telegram-login.js?5";
const CLIENT_ID = Number(import.meta.env.VITE_TG_CLIENT_ID) || 0;

export interface WidgetClaims {
  id: number;
  name?: string;
  given_name?: string;
  family_name?: string;
  preferred_username?: string;
  picture?: string;
}

interface WidgetAuth {
  idToken: string;
  user: WidgetClaims;
}

interface WidgetResult {
  id_token?: string;
  user?: WidgetClaims;
  error?: string;
}

interface TelegramLoginApi {
  auth: (options: { client_id: number; scope?: string[]; lang?: string }, callback: (result: WidgetResult) => void) => void;
}

declare global {
  interface Window {
    Telegram?: { Login?: TelegramLoginApi };
  }
}

let scriptPromise: Promise<TelegramLoginApi> | null = null;

function loadLibrary(): Promise<TelegramLoginApi> {
  if (window.Telegram?.Login) return Promise.resolve(window.Telegram.Login);
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      const api = window.Telegram?.Login;
      if (api) resolve(api);
      else reject(new Error("Telegram Login library did not initialize"));
    };
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Failed to load the Telegram Login library"));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export function isWidgetConfigured(): boolean {
  return CLIENT_ID > 0;
}

export async function openTelegramLogin(lang: string): Promise<WidgetAuth | null> {
  const api = await loadLibrary();
  return new Promise((resolve, reject) => {
    api.auth({ client_id: CLIENT_ID, scope: ["profile"], lang }, (result) => {
      if (result.id_token && result.user) resolve({ idToken: result.id_token, user: result.user });
      else if (result.error) reject(new Error(result.error));
      else resolve(null);
    });
  });
}


const OIDC_AUTH_URL = "https://oauth.telegram.org/auth";
const STATE_KEY = "mtp-login-state";

export function isCoarsePointer(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

export function redirectUri(): string {
  return `${window.location.origin}/`;
}

export function startRedirectLogin(lang: string): void {
  const state = crypto.randomUUID();
  sessionStorage.setItem(STATE_KEY, state);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: String(CLIENT_ID),
    redirect_uri: redirectUri(),
    scope: "openid profile",
    state,
    lang,
  });
  window.location.assign(`${OIDC_AUTH_URL}?${params.toString()}`);
}

export function consumeRedirectCode(): string | null {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const state = params.get("state");
  if (!code) return null;
  const expected = sessionStorage.getItem(STATE_KEY);
  sessionStorage.removeItem(STATE_KEY);
  window.history.replaceState(null, "", window.location.pathname + window.location.hash);
  if (!expected || state !== expected) {
    console.error("Telegram login: state mismatch");
    return null;
  }
  return code;
}

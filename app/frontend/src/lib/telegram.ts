import { init } from "@/init";
import { backButton, hapticFeedback, initData, openLink, postEvent, retrieveLaunchParams, retrieveRawInitData, settingsButton } from "@tma.js/sdk-react";

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  language_code?: string;
}

type NotificationType = "error" | "success" | "warning";

type SetupMethod = "web_app_setup_back_button" | "web_app_setup_settings_button";

interface TelegramButton {
  onClick: (listener: VoidFunction) => VoidFunction;
}

let insideTelegram = false;
let launchStartParam = "";

export function isInTelegram(): boolean {
  return insideTelegram;
}

export function initTelegram(): void {
  let platform: string;
  let startParam: string;
  try {
    const launchParams = retrieveLaunchParams();
    platform = launchParams.tgWebAppPlatform;
    startParam = launchParams.tgWebAppStartParam || "";
  } catch {
    insideTelegram = false;
    return;
  }
  insideTelegram = true;
  launchStartParam = startParam;
  if (location.hash.startsWith("#tgWebApp")) {
    history.replaceState(null, "", `${location.pathname}${location.search}#/`);
  }
  try {
    const debug = startParam.includes("debug") || import.meta.env.DEV;
    init({
      debug,
      eruda: debug && ["ios", "android"].includes(platform),
      mockForMacOS: platform === "macos",
    });
  } catch (error) {
    console.error("Telegram SDK initialization failed", error);
  }
  setup("web_app_setup_back_button", false);
}

export function getTelegramUser(): TelegramUser | null {
  try {
    return initData.user() ?? null;
  } catch {
    return null;
  }
}

export function getInitDataRaw(): string | null {
  try {
    return retrieveRawInitData() ?? null;
  } catch {
    return null;
  }
}

export function getStartParam(): string | null {
  return launchStartParam || null;
}

const buttonHandlers = new WeakMap<TelegramButton, (() => void)[]>();

// The SDK (3.0.8) posts a setup event only when its own state changed, and a webview reload
// restores that state from storage without posting it, so show() and hide() fall silent while
// the client keeps the header on "back". The state goes out on every change instead.
function setup(method: SetupMethod, visible: boolean): void {
  try {
    postEvent(method, { is_visible: visible });
  } catch {}
}

function bindButton(button: TelegramButton, method: SetupMethod, handler: () => void): () => void {
  let stack = buttonHandlers.get(button);
  if (!stack) {
    const created: (() => void)[] = [];
    try {
      button.onClick(() => created[created.length - 1]?.());
    } catch {
      return () => {};
    }
    buttonHandlers.set(button, created);
    stack = created;
  }
  const handlers = stack;
  if (handlers.length === 0) setup(method, true);
  handlers.push(handler);
  return () => {
    const index = handlers.lastIndexOf(handler);
    if (index < 0) return;
    handlers.splice(index, 1);
    if (handlers.length === 0) setup(method, false);
  };
}

export function bindBackButton(handler: () => void): () => void {
  return bindButton(backButton, "web_app_setup_back_button", handler);
}

export function bindSettingsButton(handler: () => void): () => void {
  return bindButton(settingsButton, "web_app_setup_settings_button", handler);
}

export function notify(type: NotificationType): void {
  try {
    if (hapticFeedback.notificationOccurred.isAvailable()) hapticFeedback.notificationOccurred(type);
  } catch {}
}

export function openExternal(url: string): void {
  if (isInTelegram()) {
    try {
      if (openLink.isAvailable()) {
        openLink(url);
        return;
      }
    } catch {}
  }
  window.open(url, "_blank", "noopener");
}

export function tick(): void {
  if (isInTelegram()) {
    try {
      if (hapticFeedback.impactOccurred.isAvailable()) hapticFeedback.impactOccurred("light");
    } catch {}
    return;
  }
  if (typeof navigator.vibrate === "function") navigator.vibrate(5);
}

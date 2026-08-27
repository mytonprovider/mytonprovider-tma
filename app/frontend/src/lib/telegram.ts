import { init } from "@/init";
import { backButton, hapticFeedback, initData, retrieveLaunchParams, retrieveRawInitData, settingsButton } from "@tma.js/sdk-react";

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  language_code?: string;
}

type NotificationType = "error" | "success" | "warning";

interface TelegramButton {
  show: { (): void; isAvailable: () => boolean };
  hide: { (): void; isAvailable: () => boolean };
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
  try {
    if (backButton.hide.isAvailable()) backButton.hide();
  } catch {}
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

interface ButtonState {
  handlers: (() => void)[];
  off: () => void;
}

const buttonStates = new WeakMap<TelegramButton, ButtonState>();

function bindButton(button: TelegramButton, handler: () => void): () => void {
  let state = buttonStates.get(button);
  if (!state) {
    state = { handlers: [], off: () => {} };
    buttonStates.set(button, state);
  }
  const current = state;
  const wasEmpty = current.handlers.length === 0;
  current.handlers.push(handler);
  if (wasEmpty) {
    try {
      if (button.show.isAvailable()) button.show();
      current.off = button.onClick(() => current.handlers[current.handlers.length - 1]?.());
    } catch {
      current.handlers.pop();
      return () => {};
    }
  }
  return () => {
    const index = current.handlers.lastIndexOf(handler);
    if (index < 0) return;
    current.handlers.splice(index, 1);
    if (current.handlers.length > 0) return;
    try {
      current.off();
      if (button.hide.isAvailable()) button.hide();
    } catch {}
    current.off = () => {};
  };
}

export function bindBackButton(handler: () => void): () => void {
  return bindButton(backButton, handler);
}

export function bindSettingsButton(handler: () => void): () => void {
  return bindButton(settingsButton, handler);
}

export function notify(type: NotificationType): void {
  try {
    if (hapticFeedback.notificationOccurred.isAvailable()) hapticFeedback.notificationOccurred(type);
  } catch {}
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

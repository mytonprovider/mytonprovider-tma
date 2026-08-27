import { type AlertSettingsPayload, BackendError, type NamesPayload, backend } from "@/data/backend";
import type { Explorer, Theme } from "@/stores/settings";
import { ALERT_TYPES, DEFAULT_THRESHOLD, type AlertTypeMap, type ThresholdMap } from "@/data/alerts";
import { normalizeLang } from "@/i18n";
import type { AlertKey, Lang } from "@/i18n/types";
import { toUserFriendly } from "@/lib/address";
import { useAlerts } from "@/stores/alerts";
import { useAuth } from "@/stores/auth";
import { useSettings } from "@/stores/settings";
import { useFavorites } from "@/stores/favorites";
import { useNames } from "@/stores/names";
import { useSubscriptions } from "@/stores/subscriptions";
import { useTrusted } from "@/stores/trusted";

let chain: Promise<unknown> = Promise.resolve();

function queue(label: string, action: () => Promise<unknown>): void {
  if (!useAuth.getState().token) return;
  chain = chain.then(action).catch((error: unknown) => console.error(`${label} failed`, error));
}

function toAlertMaps(payload: AlertSettingsPayload): { types: AlertTypeMap; thresholds: ThresholdMap } {
  const types = {} as AlertTypeMap;
  const thresholds: ThresholdMap = {};
  for (const type of ALERT_TYPES) {
    types[type.key] = payload.types.includes(type.key);
    if (type.threshold) thresholds[type.key] = payload.thresholds[type.key] ?? DEFAULT_THRESHOLD;
  }
  return { types, thresholds };
}

function serializeAlerts(): AlertSettingsPayload {
  const state = useAlerts.getState();
  return {
    enabled: state.enabled,
    types: ALERT_TYPES.filter((a) => state.types[a.key]).map((a) => a.key),
    thresholds: Object.fromEntries(
      ALERT_TYPES.filter((a) => a.threshold).map((a) => [a.key, state.thresholds[a.key] ?? DEFAULT_THRESHOLD]),
    ),
  };
}

const MIGRATED_KEY = "mtp-favorites-migrated";

function merge(remote: string[], local: string[]): string[] {
  return [...new Set([...remote, ...local])];
}

function namesPayload(): NamesPayload {
  const { providers, addresses } = useNames.getState();
  return { providers, addresses };
}

export async function hydrateFromServer(adoptPreferences = false): Promise<void> {
  flushAlerts();
  await chain;
  let profile: Awaited<ReturnType<typeof backend.profile>>;
  try {
    profile = await backend.profile();
  } catch (error) {
    if (error instanceof BackendError && error.detail === "Banned") useAuth.getState().setBanned(true);
    throw error;
  }
  useAuth.getState().setBanned(false);
  useAuth.getState().setAdmin(profile.is_admin);
  if (!localStorage.getItem(MIGRATED_KEY)) {
    const favorites = useFavorites.getState().favorites;
    const trusted = useTrusted.getState().addresses;
    const names = namesPayload();
    if (favorites.length > 0) profile = await backend.putFavorites(merge(profile.favorites, favorites));
    if (trusted.length > 0) profile = await backend.putTrusted(merge(profile.trusted_addresses, trusted));
    if (Object.keys(names.providers).length > 0 || Object.keys(names.addresses).length > 0) {
      profile = await backend.putNames({
        providers: { ...profile.names.providers, ...names.providers },
        addresses: { ...profile.names.addresses, ...names.addresses },
      });
    }
    localStorage.setItem(MIGRATED_KEY, "1");
  }
  useFavorites.getState().setAll(profile.favorites);
  useTrusted.getState().setAll(profile.trusted_addresses);
  useNames.getState().setAll(profile.names.providers, profile.names.addresses);
  useSubscriptions
    .getState()
    .setAll(profile.subscriptions.map((s) => ({ pubkey: s.pubkey, alertsEnabled: s.alerts_enabled })));
  const { types, thresholds } = toAlertMaps(profile.alerts);
  useAlerts.getState().setAll(profile.alerts.enabled, types, thresholds);
  if (adoptPreferences) {
    useSettings.setState({
      lang: normalizeLang(profile.language_code),
      langAuto: false,
      explorer: profile.explorer,
      ...(profile.theme === "auto" ? {} : { theme: profile.theme, themeAuto: false }),
    });
  }
}

export function toggleFavorite(pubkey: string): void {
  useFavorites.getState().toggle(pubkey);
  const favorites = useFavorites.getState().favorites;
  queue("favorites sync", () => backend.putFavorites(favorites));
}

export function toggleTrusted(address: string): void {
  const key = toUserFriendly(address);
  useTrusted.getState().toggle(key);
  const addresses = useTrusted.getState().addresses;
  queue("trusted sync", () => backend.putTrusted(addresses));
  if (!addresses.includes(key) && useNames.getState().addresses[key]) setAddressName(key, "");
}

export function setProviderName(pubkey: string, name: string): void {
  useNames.getState().setProvider(pubkey, name);
  const names = namesPayload();
  queue("names sync", () => backend.putNames(names));
}

export function setAddressName(address: string, name: string): void {
  useNames.getState().setAddress(address, name);
  const names = namesPayload();
  queue("names sync", () => backend.putNames(names));
}

export function toggleBell(pubkey: string): void {
  useSubscriptions.getState().toggleAlert(pubkey);
  const enabled = !useSubscriptions.getState().alertsOff.includes(pubkey);
  queue("subscription patch", () => backend.patchSubscription(pubkey, enabled));
}

export function unsubscribeProvider(pubkey: string): void {
  useSubscriptions.getState().unsubscribe(pubkey);
  queue("unsubscribe", () => backend.unsubscribe(pubkey));
}

export async function subscribeWithPassword(pubkey: string, password: string): Promise<void> {
  const entry = await backend.subscribe(pubkey, password);
  useSubscriptions.getState().subscribe(entry.pubkey);
}

export function saveAlerts(): void {
  if (alertsPushTimer) {
    clearTimeout(alertsPushTimer);
    alertsPushTimer = null;
  }
  queue("alerts save", () => backend.putAlerts(serializeAlerts()));
}

const ALERTS_PUSH_DELAY_MS = 600;
let alertsPushTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleAlertsPush(): void {
  if (alertsPushTimer) clearTimeout(alertsPushTimer);
  alertsPushTimer = setTimeout(flushAlerts, ALERTS_PUSH_DELAY_MS);
}

export function flushAlerts(): void {
  if (!alertsPushTimer) return;
  clearTimeout(alertsPushTimer);
  alertsPushTimer = null;
  queue("alerts save", () => backend.putAlerts(serializeAlerts()));
}

export function setAlertsEnabled(enabled: boolean): void {
  useAlerts.getState().setEnabled(enabled);
  scheduleAlertsPush();
}

export function toggleAlertType(key: AlertKey): void {
  useAlerts.getState().toggleType(key);
  scheduleAlertsPush();
}

export function setAlertThreshold(key: AlertKey, value: number): void {
  useAlerts.getState().setThreshold(key, value);
  scheduleAlertsPush();
}

export function setLanguage(lang: Lang): void {
  useSettings.getState().setLang(lang);
  queue("language sync", () => backend.patchProfile({ language_code: lang }));
}

export function setTheme(theme: Theme): void {
  useSettings.getState().setTheme(theme);
  queue("theme sync", () => backend.patchProfile({ theme }));
}

export function setExplorer(explorer: Explorer): void {
  useSettings.getState().setExplorer(explorer);
  queue("explorer sync", () => backend.patchProfile({ explorer }));
}

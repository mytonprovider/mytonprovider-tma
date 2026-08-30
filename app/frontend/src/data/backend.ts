import { useAuth } from "@/stores/auth";
import type { Explorer, Theme } from "@/stores/settings";

const BACKEND_BASE = import.meta.env.VITE_BACKEND_BASE ?? "";
const TIMEOUT_MS = 15000;
const CSRF_COOKIE = "starlette_admin_csrftoken";

function readCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

export class BackendError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`Backend failed with ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuth.getState().token;
  const response = await fetch(`${BACKEND_BASE}${path}`, {
    ...init,
    signal: AbortSignal.timeout?.(TIMEOUT_MS),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = (body as { detail?: unknown } | null)?.detail;
    throw new BackendError(response.status, typeof detail === "string" ? detail : path);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

type ServerTheme = Theme | "auto";

interface SubscriptionEntry {
  pubkey: string;
  alerts_enabled: boolean;
}

export interface NamesPayload {
  providers: Record<string, string>;
  addresses: Record<string, string>;
}

export interface AlertSettingsPayload {
  enabled: boolean;
  types: string[];
  thresholds: Record<string, number>;
}

export interface ChannelEntry {
  address: string;
  title: string | null;
  invite_link: string;
}

interface ProfilePayload {
  is_admin: boolean;
  language_code: string;
  theme: ServerTheme;
  explorer: Explorer;
  favorites: string[];
  trusted_addresses: string[];
  channels: ChannelEntry[];
  names: NamesPayload;
  alerts: AlertSettingsPayload;
  subscriptions: SubscriptionEntry[];
}

interface ProfilePatch {
  language_code?: string;
  theme?: ServerTheme;
  explorer?: Explorer;
}

interface OwnerLoad {
  cpu: number | null;
  ram: number | null;
  net_mbps: number | null;
  net_pct: number | null;
  disk: number | null;
}

export interface OwnerTriggerEntry {
  key: string;
  color: "red" | "orange";
}

export interface OwnerChartPoint {
  t: number;
  cpu: number | null;
  cpu_max: number | null;
  ram: number | null;
  ram_max: number | null;
  net_mbps: number | null;
  net_max: number | null;
  net_in_mbps: number | null;
  net_out_mbps: number | null;
  disk: number | null;
  disk_max: number | null;
}

export interface OwnerSummary {
  earned: number | null;
  bags_added: number;
  traffic_in: number | null;
  traffic_out: number | null;
  storage_growth_bytes: number | null;
}

interface OwnerAllTime {
  earned: number | null;
  traffic: number | null;
  stored_bytes: number | null;
}

export interface ProviderPayload {
  balance: number | null;
  balance_updated_at: number | null;
  earned: number | null;
  income: number;
  income_max: number | null;
  wallet_address: string | null;
  telemetry_updated_at: number | null;
  load: OwnerLoad;
  triggers: OwnerTriggerEntry[];
  monthly: OwnerSummary;
  all_time: OwnerAllTime;
  bags: BagCounters;
}

export interface StatsPayload {
  summary: OwnerSummary;
}

export interface ChartPayload {
  points: OwnerChartPoint[];
}

export interface OwnerPayload extends ProviderPayload {
  summary: OwnerSummary;
  chart: OwnerChartPoint[];
}

export type SlotState =
  | "confirmed"
  | "closed"
  | "not_paid"
  | "not_accepted"
  | "unavailable"
  | "not_confirmed"
  | "downloading";

// A bag says "partial" when its slots disagree and "not_hired" when nobody is hired
// yet; a single slot can be in neither.
export type BagState = SlotState | "partial" | "not_hired";

// Screen slices, not states: "all" and "check" only narrow the list.
export type BagFilter = SlotState | "all" | "check";

export interface BagCounters {
  all: number;
  confirmed: number;
  closed: number;
  not_paid: number;
  not_accepted: number;
  unavailable: number;
  not_confirmed: number;
  downloading: number;
  check: number;
}

export const EMPTY_BAGS: BagCounters = {
  all: 0,
  confirmed: 0,
  closed: 0,
  not_paid: 0,
  not_accepted: 0,
  unavailable: 0,
  not_confirmed: 0,
  downloading: 0,
  check: 0,
};

export interface Bag {
  bag_id: string | null;
  address: string;
  owner_address: string | null;
  size: number | null;
  state: SlotState;
  balance: number | null;
  rate_per_mb_day: number | null;
  payment_max_span: number | null;
  hired_at: number | null;
  last_proof_at: number | null;
  reason: number | null;
  reason_at: number | null;
}

interface BagsPayload {
  items: Bag[];
  total: number;
}

export interface BagProvider {
  pubkey: string;
  state: SlotState;
  payment_max_span: number | null;
  rate_per_mb_day: number | null;
  last_proof_at: number | null;
  next_proof_byte: number | null;
  // uint64 from the contract: a JSON number would lose it past 2^53.
  nonce: string | null;
  reason: number | null;
  reason_at: number | null;
}

export interface BagPayload {
  contract_address: string;
  bag_id: string | null;
  state: BagState;
  owner_address: string | null;
  size: number | null;
  chunk_size: number | null;
  merkle_hash: string | null;
  key_len: number | null;
  balance: number | null;
  providers: BagProvider[];
}

async function adminPost(path: string): Promise<void> {
  await request<void>("/admin/csrf");
  await request<void>(path, { method: "POST", headers: { "X-CSRFToken": readCookie(CSRF_COOKIE) } });
}

export const backend = {
  authTelegram: (initDataRaw: string) =>
    request<{ token: string }>("/api/v1/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ init_data: initDataRaw }),
    }),
  authWidget: (idToken: string) =>
    request<{ token: string }>("/api/v1/auth/widget", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),
  authCode: (code: string, redirectUri: string) =>
    request<{ token: string; name: string | null; username: string | null; photo_url: string | null }>(
      "/api/v1/auth/code",
      { method: "POST", body: JSON.stringify({ code, redirect_uri: redirectUri }) },
    ),
  refresh: () => request<{ token: string }>("/api/v1/auth/refresh", { method: "POST" }),
  adminSession: () => adminPost("/admin/session"),
  adminLogout: () => adminPost("/admin/logout"),
  profile: () => request<ProfilePayload>("/api/v1/profile"),
  patchProfile: (patch: ProfilePatch) =>
    request<ProfilePayload>("/api/v1/profile", { method: "PATCH", body: JSON.stringify(patch) }),
  putFavorites: (favorites: string[]) =>
    request<ProfilePayload>("/api/v1/profile/favorites", { method: "PUT", body: JSON.stringify({ favorites }) }),
  putTrusted: (addresses: string[]) =>
    request<ProfilePayload>("/api/v1/profile/trusted-addresses", {
      method: "PUT",
      body: JSON.stringify({ trusted_addresses: addresses }),
    }),
  putNames: (names: NamesPayload) =>
    request<ProfilePayload>("/api/v1/profile/names", { method: "PUT", body: JSON.stringify(names) }),
  putAlerts: (settings: AlertSettingsPayload) =>
    request<ProfilePayload>("/api/v1/profile/alerts", { method: "PUT", body: JSON.stringify(settings) }),
  subscribe: (pubkey: string, password: string) =>
    request<SubscriptionEntry>("/api/v1/profile/subscriptions", {
      method: "POST",
      body: JSON.stringify({ pubkey, password }),
    }),
  unsubscribe: (pubkey: string) => request<void>(`/api/v1/profile/subscriptions/${pubkey}`, { method: "DELETE" }),
  patchSubscription: (pubkey: string, alertsEnabled: boolean) =>
    request<SubscriptionEntry>(`/api/v1/profile/subscriptions/${pubkey}`, {
      method: "PATCH",
      body: JSON.stringify({ alerts_enabled: alertsEnabled }),
    }),
  provider: (pubkey: string) => request<ProviderPayload>(`/api/v1/provider/${pubkey}`),
  providerStats: (pubkey: string, period: string) =>
    request<StatsPayload>(`/api/v1/provider/${pubkey}/stats?period=${period}`),
  providerChart: (pubkey: string, range: string) =>
    request<ChartPayload>(`/api/v1/provider/${pubkey}/chart?range=${range}`),
  providerBags: (pubkey: string, state: BagFilter, offset: number, query: string) =>
    request<BagsPayload>(
      `/api/v1/provider/${pubkey}/bags?state=${state}&offset=${offset}` +
        (query ? `&q=${encodeURIComponent(query)}` : ""),
    ),
  bag: (query: string) => request<BagPayload>(`/api/v1/bag/${encodeURIComponent(query)}`),
};

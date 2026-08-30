interface Location {
  country: string;
  countryIso: string;
  city: string;
  timeZone: string;
}

export interface StatusReason {
  reason: number;
  count: number;
}

export interface Telemetry {
  storageGitHash: string | null;
  providerGitHash: string | null;
  totalSpaceBytes: number | null;
  usedSpaceBytes: number | null;
  updatedAt: number | null;
  cpuName: string | null;
  cpuCount: number | null;
  cpuVirtual: boolean | null;
  totalRamBytes: number | null;
  usageRamBytes: number | null;
  diskRead: string | null;
  diskWrite: string | null;
  downloadSpeed: number | null;
  uploadSpeed: number | null;
  ping: number | null;
  country: string | null;
  isp: string | null;
}

export interface Provider {
  pubkey: string;
  address: string;
  status: number | null;
  statusRatio: number | null;
  location: Location | null;
  uptime: number;
  workingTime: number;
  rating: number;
  price: number;
  minSpan: number;
  maxSpan: number;
  maxBagBytes: number;
  regTime: number;
  lastOnlineCheckTime: number | null;
  hasTelemetry: boolean;
  telemetry: Telemetry;
  statusReasons: StatusReason[];
  staleSec: number;
  telemetryStaleSec: number;
}

export type SortField = "rating" | "uptime" | "price" | "working_time";
type SortDir = "asc" | "desc";

export interface Sort {
  field: SortField;
  dir: SortDir;
}

export type Range = [number, number];

// The one place range filters are listed: every map keyed by RangeKey (query.ts metrics,
// bounds, sliders) has to cover it, so a filter added here cannot be half-wired.
export const RANGE_KEYS = [
  "rating",
  "uptime",
  "price",
  "bag",
  "cores",
  "ram",
  "age",
  "minSpan",
  "maxSpan",
  "space",
  "diskRead",
  "diskWrite",
  "download",
  "upload",
  "ping",
] as const;

export type RangeKey = (typeof RANGE_KEYS)[number];

export type CatalogFilters = Record<RangeKey, Range | null> & {
  location: string | null;
  cpuVirtual: boolean | null;
  storageHash: string | null;
  providerHash: string | null;
  freeSpace: boolean;
  telemetry: boolean | null;
  stableOnly: boolean;
};

export type FilterBounds = Record<RangeKey, Range>;

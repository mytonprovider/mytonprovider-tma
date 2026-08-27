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
  statusRatio: number;
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

export interface CatalogFilters {
  location: string | null;
  rating: Range | null;
  uptime: Range | null;
  price: Range | null;
  bag: Range | null;
  cores: Range | null;
  ram: Range | null;
  age: Range | null;
  minSpan: Range | null;
  maxSpan: Range | null;
  space: Range | null;
  diskRead: Range | null;
  diskWrite: Range | null;
  download: Range | null;
  upload: Range | null;
  ping: Range | null;
  cpuVirtual: boolean | null;
  storageHash: string | null;
  providerHash: string | null;
  freeSpace: boolean;
  telemetry: boolean | null;
  stableOnly: boolean;
}

export interface FilterBounds {
  rating: Range;
  uptime: Range;
  price: Range;
  bag: Range;
  cores: Range;
  ram: Range;
  age: Range;
  minSpan: Range;
  maxSpan: Range;
  space: Range;
  diskRead: Range;
  diskWrite: Range;
  download: Range;
  upload: Range;
  ping: Range;
}

import { BITS_IN_MBIT, BYTES_IN_GIB, NANO, PING_MAX, diskSpeedToNum } from "@/lib/format";
import { statusTone } from "@/lib/status";
import { RANGE_KEYS, type CatalogFilters, type FilterBounds, type Provider, type Range, type RangeKey, type Sort } from "./types";

const FREE_SPACE_BYTES = 100 * BYTES_IN_GIB;


function toUnits(bytes: number | null, factor: number): number | null {
  return bytes === null ? null : bytes / factor;
}

function diskMiB(text: string | null): number | null {
  const value = diskSpeedToNum(text);
  return value === null ? null : value / 1048576;
}

const METRIC: Record<RangeKey, (p: Provider) => number | null> = {
  rating: (p) => p.rating,
  uptime: (p) => p.uptime,
  price: (p) => p.price / NANO,
  bag: (p) => p.maxBagBytes / BYTES_IN_GIB,
  cores: (p) => p.telemetry.cpuCount,
  ram: (p) => toUnits(p.telemetry.totalRamBytes, BYTES_IN_GIB),
  age: (p) => (Date.now() / 1000 - p.regTime) / 86400,
  minSpan: (p) => p.minSpan / 86400,
  maxSpan: (p) => p.maxSpan / 86400,
  space: (p) => toUnits(p.telemetry.totalSpaceBytes, BYTES_IN_GIB),
  diskRead: (p) => diskMiB(p.telemetry.diskRead),
  diskWrite: (p) => diskMiB(p.telemetry.diskWrite),
  download: (p) => toUnits(p.telemetry.downloadSpeed, BITS_IN_MBIT),
  upload: (p) => toUnits(p.telemetry.uploadSpeed, BITS_IN_MBIT),
  ping: (p) => (p.telemetry.ping !== null && p.telemetry.ping < PING_MAX ? p.telemetry.ping : null),
};

const FROM_MIN: Partial<Record<RangeKey, boolean>> = { rating: true, price: true, cores: true };

function hasFreeSpace(p: Provider): boolean {
  if (!p.hasTelemetry) return false;
  const total = p.telemetry.totalSpaceBytes ?? 0;
  const used = p.telemetry.usedSpaceBytes ?? 0;
  return total - used > FREE_SPACE_BYTES;
}

function within(value: number | null, range: Range, bound: Range | undefined): boolean {
  if (value === null || !Number.isFinite(value)) return false;
  const clamped = bound ? Math.max(bound[0], Math.min(value, bound[1])) : value;
  return clamped >= range[0] && clamped <= range[1];
}

function matchesFilters(p: Provider, f: CatalogFilters, b: FilterBounds | null): boolean {
  const tm = p.telemetry;
  if (f.location && p.location?.countryIso !== f.location) return false;
  for (const key of RANGE_KEYS) {
    const range = f[key];
    if (range && !within(METRIC[key](p), range, b?.[key])) return false;
  }
  if (f.cpuVirtual !== null && tm.cpuVirtual !== f.cpuVirtual) return false;
  if (f.storageHash && tm.storageGitHash !== f.storageHash) return false;
  if (f.providerHash && tm.providerGitHash !== f.providerHash) return false;
  if (f.freeSpace && !hasFreeSpace(p)) return false;
  if (f.telemetry !== null && p.hasTelemetry !== f.telemetry) return false;
  if (f.stableOnly && statusTone(p) !== "green") return false;
  return true;
}

function boundOf(values: (number | null)[], fromMin: boolean): Range {
  const sorted = values.filter((v): v is number => v !== null && Number.isFinite(v)).sort((a, b) => a - b);
  if (!sorted.length) return [0, 1];
  const p95 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))];
  const lo = fromMin ? Math.floor(sorted[0]) : 0;
  return [lo, Math.max(lo + 1, Math.ceil(p95))];
}

export function computeRanks(providers: Provider[]): Record<string, number> {
  const ranked = providers.filter((p) => p.rating > 0).sort((a, b) => b.rating - a.rating);
  const ranks: Record<string, number> = {};
  ranked.forEach((p, index) => {
    ranks[p.pubkey] = index + 1;
  });
  return ranks;
}

export function computeBounds(providers: Provider[]): FilterBounds {
  const bounds = { uptime: [0, 100] as Range } as FilterBounds;
  for (const key of RANGE_KEYS) {
    if (key === "uptime") continue;
    bounds[key] = boundOf(
      providers.map((p) => METRIC[key](p)),
      FROM_MIN[key] ?? false,
    );
  }
  return bounds;
}

const SORT_VALUE: Record<Sort["field"], (p: Provider) => number> = {
  rating: (p) => p.rating,
  uptime: (p) => p.uptime,
  price: (p) => p.price,
  working_time: (p) => p.workingTime,
};

function sortProviders(list: Provider[], sort: Sort): Provider[] {
  const value = SORT_VALUE[sort.field];
  return [...list].sort((a, b) => (sort.dir === "asc" ? value(a) - value(b) : value(b) - value(a)));
}

interface CatalogSelection {
  // null = whole catalog; a list restricts the tab to its own pubkeys
  only: string[] | null;
  search: string;
  filters: CatalogFilters;
  sort: Sort;
  names: Record<string, string>;
  bounds: FilterBounds | null;
}

export function selectCatalog(providers: Provider[], selection: CatalogSelection): Provider[] {
  const search = selection.search.trim().toLowerCase();
  const found = (p: Provider) =>
    p.pubkey.toLowerCase().includes(search) || (selection.names[p.pubkey] ?? "").toLowerCase().includes(search);
  const filtered = providers.filter((p) => {
    if (selection.only && !selection.only.includes(p.pubkey)) return false;
    if (search && !found(p)) return false;
    return matchesFilters(p, selection.filters, selection.bounds);
  });
  return sortProviders(filtered, selection.sort);
}

export function countActiveFilters(f: CatalogFilters): number {
  let count = 0;
  if (f.location) count++;
  for (const key of RANGE_KEYS) {
    if (f[key]) count++;
  }
  if (f.cpuVirtual !== null) count++;
  if (f.storageHash) count++;
  if (f.providerHash) count++;
  if (f.freeSpace) count++;
  if (f.telemetry !== null) count++;
  if (f.stableOnly) count++;
  return count;
}

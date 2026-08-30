import type { TriggerKey } from "@/i18n/types";
import { ACCENT, SC } from "@/lib/colors";
import { EMPTY, NANO, amount, formatBytes, formatPriceGram, formatSpace, spacePair } from "@/lib/format";
import { defaultThreshold, type ThresholdMap } from "./alerts";
import type { OwnerChartPoint, OwnerPayload, OwnerSummary, OwnerTriggerEntry } from "./backend";
import type { Provider } from "./types";

export type OwnerPeriod = "hour" | "today" | "week" | "month";
export type OwnerChartRange = "1h" | "6h" | "12h" | "24h";

export const OWNER_CHART_RANGES: { value: OwnerChartRange; hours: number }[] = [
  { value: "1h", hours: 1 },
  { value: "6h", hours: 6 },
  { value: "12h", hours: 12 },
  { value: "24h", hours: 24 },
];

export type GaugeKey = "cpu_high" | "ram_high" | "disk_load_high" | "network_high";
export type ChartKey = "cpu_high" | "ram_high" | "disk_load_high" | "net_in" | "net_out";

export const OWNER_PERIOD_API: Record<OwnerPeriod, string> = {
  hour: "hour",
  today: "day",
  week: "week",
  month: "month",
};

interface OwnerGaugeData {
  key: GaugeKey;
  value: number | null;
  threshold: number;
}

interface OwnerChartData {
  key: ChartKey;
  values: (number | null)[];
  peaks: (number | null)[];
  times: number[];
  threshold: number | null;
  unit: string;
  current: string;
}

interface OwnerData {
  balance: string;
  balanceUpdatedAt: number | null;
  income: string;
  incomeMax: string | null;
  usedSpace: string;
  totalSpace: string;
  spaceUnit: string;
  spaceKnown: boolean;
  usedPct: number;
  barColor: string;
  spaceOver: boolean;
  summary: { earned: string; bagsAdded: string; trafficIn: string; trafficOut: string; storageGrowth: string };
  monthly: { earned: string; space: string; traffic: string };
  allTime: { earned: string; space: string; traffic: string };
  gauges: OwnerGaugeData[];
  charts: OwnerChartData[];
}

const TRIGGER_KEYS: ReadonlySet<string> = new Set([
  "telemetry_lost",
  "not_online",
  "cpu_high",
  "ram_high",
  "network_high",
  "disk_load_high",
  "disk_space_low",
]);

interface OwnerTrigger {
  key: TriggerKey;
  color: "red" | "orange";
}

export function ownerTriggers(entries: OwnerTriggerEntry[]): OwnerTrigger[] {
  return entries
    .filter((entry): entry is OwnerTriggerEntry & { key: TriggerKey } => TRIGGER_KEYS.has(entry.key))
    .map((entry) => ({ key: entry.key, color: entry.color }));
}

const GAUGE_KEYS: GaugeKey[] = ["cpu_high", "ram_high", "disk_load_high", "network_high"];

function formatGram(nano: number | null): string {
  return nano != null ? formatPriceGram(nano) : EMPTY;
}

function formatGrowth(bytes: number | null): string {
  if (bytes == null) return EMPTY;
  return `${bytes >= 0 ? "+" : "-"}${formatSpace(Math.abs(bytes))}`;
}

function summaryBlock(summary: OwnerSummary) {
  return {
    earned: formatGram(summary.earned),
    bagsAdded: `+${summary.bags_added}`,
    trafficIn: formatBytes(summary.traffic_in),
    trafficOut: formatBytes(summary.traffic_out),
    storageGrowth: formatGrowth(summary.storage_growth_bytes),
  };
}

function gaugeValues(payload: OwnerPayload): Record<GaugeKey, number | null> {
  return {
    cpu_high: payload.load.cpu,
    ram_high: payload.load.ram,
    disk_load_high: payload.load.disk,
    network_high: payload.load.net_pct,
  };
}

const CHART_KEYS: ChartKey[] = ["cpu_high", "ram_high", "disk_load_high", "net_in", "net_out"];

const CHART_FIELDS: Record<ChartKey, [keyof OwnerChartPoint, keyof OwnerChartPoint | null]> = {
  cpu_high: ["cpu", "cpu_max"],
  ram_high: ["ram", "ram_max"],
  disk_load_high: ["disk", "disk_max"],
  net_in: ["net_in_mbps", null],
  net_out: ["net_out_mbps", null],
};

function chartValue(point: OwnerChartPoint, field: keyof OwnerChartPoint, digits: number): number | null {
  const value = point[field];
  if (value === null) return null;
  const factor = 10 ** digits;
  return Math.max(0, Math.round(value * factor) / factor);
}

function lastValue(values: (number | null)[]): number | null {
  for (let index = values.length - 1; index >= 0; index--) {
    const value = values[index];
    if (value !== null) return value;
  }
  return null;
}

function threshold(thresholds: ThresholdMap, key: GaugeKey): number {
  return thresholds[key] ?? defaultThreshold(key);
}

export function adaptOwner(p: Provider, payload: OwnerPayload, thresholds: ThresholdMap): OwnerData {
  const usedBytes = p.telemetry.usedSpaceBytes ?? 0;
  const totalBytes = p.telemetry.totalSpaceBytes ?? 0;
  const usedPct = totalBytes > 0 ? Math.min(100, (usedBytes / totalBytes) * 100) : 0;
  const usedPctRound = Math.round(usedPct);
  const pair = spacePair(usedBytes, totalBytes);
  const spaceThreshold = thresholds.disk_space_low ?? defaultThreshold("disk_space_low");
  const barColor = usedPct >= 99 ? SC.red : usedPct >= spaceThreshold ? SC.orange : ACCENT;

  const load = gaugeValues(payload);
  const monthlyTraffic =
    payload.monthly.traffic_in != null || payload.monthly.traffic_out != null
      ? (payload.monthly.traffic_in ?? 0) + (payload.monthly.traffic_out ?? 0)
      : null;

  return {
    balance: payload.balance != null ? amount(payload.balance / NANO) : EMPTY,
    balanceUpdatedAt: payload.balance_updated_at,
    income: amount(payload.income / NANO),
    incomeMax: payload.income_max != null ? amount(payload.income_max / NANO) : null,
    usedSpace: pair?.used ?? EMPTY,
    totalSpace: pair?.total ?? EMPTY,
    spaceUnit: pair?.unit ?? "",
    spaceKnown: totalBytes > 0,
    usedPct: usedPctRound,
    barColor,
    spaceOver: usedPctRound >= spaceThreshold,
    summary: summaryBlock(payload.summary),
    monthly: {
      earned: formatGram(payload.monthly.earned),
      space: formatGrowth(payload.monthly.storage_growth_bytes),
      traffic: formatBytes(monthlyTraffic),
    },
    allTime: {
      earned: formatGram(payload.all_time.earned),
      space: formatSpace(payload.all_time.stored_bytes),
      traffic: formatBytes(payload.all_time.traffic),
    },
    gauges: GAUGE_KEYS.map((key) => ({
      key,
      value: load[key] === null || load[key] === undefined ? null : Math.min(100, Math.max(0, Math.round(load[key]))),
      threshold: threshold(thresholds, key),
    })),
    charts: CHART_KEYS.map((key) => {
      const [field, peakField] = CHART_FIELDS[key];
      const network = peakField === null;
      const digits = network ? 1 : 0;
      const unit = network ? " Mbit/s" : "%";
      const values = payload.chart.map((point) => chartValue(point, field, digits));
      const peaks = peakField ? payload.chart.map((point) => chartValue(point, peakField, digits)) : values.map(() => null);
      const current = lastValue(values);
      return {
        key,
        values,
        peaks,
        times: payload.chart.map((point) => point.t),
        threshold: network ? null : threshold(thresholds, key as GaugeKey),
        unit,
        current: current !== null ? `${current}${unit}` : EMPTY,
      };
    }),
  };
}

import type { AlertGroupKey, AlertKey } from "@/i18n/types";

interface AlertType {
  key: AlertKey;
  threshold: boolean;
}

export interface AlertGroup {
  key: AlertGroupKey;
  types: AlertType[];
}

export const ALERT_GROUPS: AlertGroup[] = [
  {
    key: "availability",
    types: [
      { key: "not_online", threshold: false },
      { key: "telemetry_lost", threshold: false },
      { key: "service_restarted", threshold: false },
    ],
  },
  {
    key: "load",
    types: [
      { key: "cpu_high", threshold: true },
      { key: "ram_high", threshold: true },
      { key: "network_high", threshold: true },
      { key: "disk_load_high", threshold: true },
      { key: "disk_space_low", threshold: true },
    ],
  },
  {
    key: "bags",
    types: [
      { key: "bag_added", threshold: false },
      { key: "bag_stored", threshold: false },
      { key: "bag_slow", threshold: false },
      { key: "bag_removed", threshold: false },
      { key: "bag_unpaid", threshold: false },
      { key: "bag_refilled", threshold: false },
      { key: "bag_closed", threshold: false },
    ],
  },
  {
    key: "reports",
    types: [
      { key: "daily_report", threshold: false },
      { key: "monthly_report", threshold: false },
    ],
  },
];

export const ALERT_TYPES: AlertType[] = ALERT_GROUPS.flatMap((group) => group.types);

const DEFAULT_THRESHOLD = 90;
const THRESHOLD_OVERRIDES: Partial<Record<AlertKey, number>> = { disk_space_low: 85 };

export function defaultThreshold(key: AlertKey): number {
  return THRESHOLD_OVERRIDES[key] ?? DEFAULT_THRESHOLD;
}
export const THRESHOLD_MIN = 30;
export const THRESHOLD_MAX = 100;

export type AlertTypeMap = Record<AlertKey, boolean>;
export type ThresholdMap = Partial<Record<AlertKey, number>>;

export function defaultAlertTypes(): AlertTypeMap {
  const map = {} as AlertTypeMap;
  for (const type of ALERT_TYPES) map[type.key] = true;
  return map;
}

export function defaultThresholds(): ThresholdMap {
  const map: ThresholdMap = {};
  for (const type of ALERT_TYPES) if (type.threshold) map[type.key] = defaultThreshold(type.key);
  return map;
}

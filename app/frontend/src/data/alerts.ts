import type { AlertKey } from "@/i18n/types";

interface AlertType {
  key: AlertKey;
  threshold: boolean;
}

export const ALERT_TYPES: AlertType[] = [
  { key: "monthly_report", threshold: false },
  { key: "reward_received", threshold: false },
  { key: "bag_added", threshold: false },
  { key: "service_restarted", threshold: false },
  { key: "telemetry_lost", threshold: false },
  { key: "not_online", threshold: false },
  { key: "cpu_high", threshold: true },
  { key: "ram_high", threshold: true },
  { key: "network_high", threshold: true },
  { key: "disk_load_high", threshold: true },
  { key: "disk_space_low", threshold: true },
];

export const DEFAULT_THRESHOLD = 90;
const THRESHOLD_OVERRIDES: Partial<Record<AlertKey, number>> = { disk_space_low: 85 };
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
  for (const type of ALERT_TYPES) if (type.threshold) map[type.key] = THRESHOLD_OVERRIDES[type.key] ?? DEFAULT_THRESHOLD;
  return map;
}

import type { Dict } from "@/i18n/types";
import type { StatusTone } from "./colors";

export const BYTES_IN_GIB = 1024 ** 3;
export const BYTES_IN_GB = 1e9;
export const BITS_IN_MBIT = 1e6;
export const NANO = 1_000_000_000;
export const PING_MAX = 10000;

export const EMPTY = "—";
export const JUST_NOW_SEC = 60;
export const LEVEL_MARGIN = 12;
export const FREE_LOW = 15;
export const FREE_WARN = 25;

export function diskSpeedToNum(text: string | null): number | null {
  if (!text) return null;
  const match = text.match(/([\d.]+)\s*([KMG]i?B)/i);
  if (!match) return null;
  const mult: Record<string, number> = {
    kib: 1024,
    mib: 1048576,
    gib: 1073741824,
    kb: 1000,
    mb: 1e6,
    gb: 1e9,
  };
  return parseFloat(match[1]) * (mult[match[2].toLowerCase()] ?? 1);
}

export function formatDiskSpeed(text: string | null): string {
  const bytes = diskSpeedToNum(text);
  return bytes === null ? EMPTY : `${amount(bytes / 1048576)} MiB/s`;
}
const ELLIPSIS = "…";
export const KEY_HEAD = 6;
export const KEY_CHARS = 13;

export function trim(value: number, digits: number): string {
  return String(parseFloat(value.toFixed(digits)));
}

export function trimDown(value: number, digits: number): string {
  const scale = 10 ** digits;
  return String(Math.floor(value * scale) / scale);
}

export function amount(value: number): string {
  return trim(value, 2);
}

export function formatPrice(nanoTon: number): string {
  return amount(nanoTon / NANO);
}

export function formatPriceGram(nanoTon: number): string {
  return `${formatPrice(nanoTon)} GRAM`;
}

const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"];
const BYTE_MAX = BYTE_UNITS.length - 1;
const SPACE_MAX = BYTE_UNITS.indexOf("GB");
const ROUND_FROM = 1000;

export function scaleFor(bytes: number, maxIndex = BYTE_MAX): { divisor: number; unit: string } {
  let divisor = 1;
  let index = 0;
  while (bytes >= divisor * 1024 && index < maxIndex) {
    divisor *= 1024;
    index += 1;
  }
  return { divisor, unit: BYTE_UNITS[index] };
}

function sized(bytes: number | null, maxIndex: number): string {
  if (bytes === null || !Number.isFinite(bytes) || bytes <= 0) return EMPTY;
  const { divisor, unit } = scaleFor(bytes, maxIndex);
  const value = bytes / divisor;
  return `${trim(value, value >= ROUND_FROM ? 0 : 2)} ${unit}`;
}

export function formatBytes(bytes: number | null): string {
  return sized(bytes, BYTE_MAX);
}

export function formatSpace(bytes: number | null): string {
  return sized(bytes, SPACE_MAX);
}

export function formatTime(secs: number, t: Dict, skipLast = false): string {
  if (secs < 60) return t.sec(Math.round(secs));
  const seconds = Math.round(secs % 60);
  const minutes = Math.floor(secs / 60) % 60;
  const hours = Math.floor(secs / 3600) % 24;
  const days = Math.floor(secs / 86400) % 365;
  const years = Math.floor(secs / 31536000);
  const join = (...parts: string[]) => parts.filter(Boolean).join(" ");
  if (years > 0) return join(t.year(years), !skipLast && days ? t.days(days) : "");
  if (secs < 3600) return join(minutes ? t.min(minutes) : "", !skipLast && seconds ? t.sec(seconds) : "");
  if (secs < 86400) return join(hours ? t.hr(hours) : "", !skipLast && minutes ? t.min(minutes) : "");
  if (secs < 604800)
    return join(days ? t.days(days) : "", hours ? t.hr(hours) : "", !skipLast && minutes ? t.min(minutes) : "");
  return join(days ? t.days(days) : "", !skipLast && hours ? t.hr(hours) : "");
}

export function ago(secs: number, t: Dict): string {
  return secs < JUST_NOW_SEC ? t.justNow : t.ago(formatTime(secs, t, true));
}

export function formatMbits(bitsPerSec: number | null): string {
  return bitsPerSec && bitsPerSec > 0 ? `${Math.round(bitsPerSec / BITS_IN_MBIT)} Mbit/s` : EMPTY;
}

export function formatPing(ms: number | null): string {
  return ms && ms > 0 && ms < PING_MAX ? `${Math.round(ms)} ms` : EMPTY;
}

export function fitKey(value: string, chars: number): string {
  if (value.length <= chars) return value;
  const head = Math.min(KEY_HEAD, Math.max(1, chars - 1));
  const tail = Math.max(0, chars - head - 1);
  return `${value.slice(0, head)}${ELLIPSIS}${tail > 0 ? value.slice(value.length - tail) : ""}`;
}

export function shorten(value: string, max: number): string {
  if (!value || value.length <= max) return value || "";
  const half = Math.floor(max / 2);
  return `${value.substring(0, half)}${ELLIPSIS}${value.substring(value.length - half)}`;
}

export function spaceFreePercent(total: number | null, used: number | null): number | null {
  if (total === null || used === null || total <= 0) return null;
  return Math.min(100, Math.max(0, ((total - used) / total) * 100));
}

export function freeSpaceTone(free: number): StatusTone {
  if (free <= FREE_LOW) return "red";
  if (free <= FREE_WARN) return "orange";
  return "green";
}

export function levelTone(value: number, threshold: number): StatusTone {
  if (value >= threshold) return "red";
  if (value >= threshold - LEVEL_MARGIN) return "orange";
  return "green";
}

export function uptimeTone(uptime: number): StatusTone {
  if (uptime >= 99) return "green";
  if (uptime >= 95) return "yellow";
  if (uptime > 0) return "red";
  return "gray";
}

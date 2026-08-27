import type { Provider } from "@/data/types";
import type { Dict } from "@/i18n/types";
import { SC, type StatusTone } from "./colors";

const UNAVAILABLE = new Set([101, 102, 103, 201, 202]);
const NOT_STORED = new Set([301, 302]);
const NO_PROOF = new Set([401, 402, 403]);

type LabelKey = keyof Dict["status"];

interface ResolvedStatus {
  tone: StatusTone;
  labelKey: LabelKey;
  ratio: number;
  passed: number;
  total: number;
  dominantReason: number | null;
  problems: number;
}

export function statusTone(p: Provider): StatusTone {
  return resolveStatus(p).tone;
}

export function reasonTone(reason: number): StatusTone {
  if (NOT_STORED.has(reason)) return "red";
  if (NO_PROOF.has(reason)) return "orange";
  return "gray";
}

export function reasonText(reason: number | null, t: Dict): string {
  return (t.reason as Record<string, string | undefined>)[String(reason)] ?? t.unknownReason(reason);
}

function ratioTone(ratio: number): StatusTone {
  return ratio >= 0.99 ? "green" : ratio >= 0.8 ? "yellow" : "red";
}

function resolveStatus(p: Provider): ResolvedStatus {
  const valid = p.statusReasons.find((r) => r.reason === 0)?.count ?? 0;
  const total = p.statusReasons.reduce((sum, r) => sum + r.count, 0);
  const ratio =
    p.statusRatio != null ? p.statusRatio : total > 0 ? valid / total : p.status === 0 ? 1 : 0;

  let tone: StatusTone = "gray";
  let labelKey: LabelKey = "noData";
  if (p.status !== null) {
    if (p.status === 0) {
      tone = ratioTone(ratio);
      labelKey = tone === "green" ? "stable" : tone === "yellow" ? "partial" : "unstable";
    } else if (UNAVAILABLE.has(p.status)) {
      tone = "gray";
      labelKey = "unavailable";
    } else if (NOT_STORED.has(p.status)) {
      tone = "red";
      labelKey = "notStored";
    } else if (NO_PROOF.has(p.status)) {
      tone = "orange";
      labelKey = "noProofs";
    } else {
      tone = "gray";
      labelKey = "unknown";
    }
  }

  const sorted = [...p.statusReasons].sort((a, b) => b.count - a.count);
  let dominantReason: number | null = null;
  if (sorted.length > 0) {
    dominantReason =
      sorted[0].count < total * 0.8 && sorted.length > 1 ? sorted[1].reason : sorted[0].reason;
  }

  const problems = p.statusReasons
    .filter((r) => NOT_STORED.has(r.reason) || NO_PROOF.has(r.reason))
    .reduce((sum, r) => sum + r.count, 0);

  return { tone, labelKey, ratio, passed: valid, total, dominantReason, problems };
}

interface StatusView {
  tone: StatusTone;
  color: string;
  checksColor: string;
  label: string;
  desc: string;
  ratio: number;
  hasRatio: boolean;
  passed: number;
  total: number;
}

export function describeStatus(p: Provider, t: Dict): StatusView {
  const s = resolveStatus(p);
  const desc = s.problems > 0 ? t.bagsFailed : s.total === 0 ? t.reason.none : reasonText(s.dominantReason, t);
  return {
    tone: s.tone,
    color: SC[s.tone],
    checksColor: SC[ratioTone(s.ratio)],
    label: t.status[s.labelKey],
    desc,
    ratio: s.ratio,
    hasRatio: p.status === 0 && s.total > 0,
    passed: s.passed,
    total: s.total,
  };
}

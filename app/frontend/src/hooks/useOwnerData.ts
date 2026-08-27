import {
  BackendError,
  backend,
  type ChartPayload,
  type OwnerPayload,
  type ProviderPayload,
  type StatsPayload,
} from "@/data/backend";
import { OWNER_PERIOD_API, type OwnerChartRange, type OwnerPeriod } from "@/data/owner";
import { useAuth } from "@/stores/auth";
import { useEffect, useRef, useState } from "react";
import { create } from "zustand";

const CACHE_TTL_MS = 60_000;
const cache = new Map<string, { at: number; payload: unknown }>();
const inflight = new Map<string, Promise<unknown>>();

function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.at < CACHE_TTL_MS) return Promise.resolve(entry.payload as T);
  let request = inflight.get(key);
  if (!request) {
    request = load()
      .then((payload) => {
        cache.set(key, { at: Date.now(), payload });
        return payload;
      })
      .finally(() => inflight.delete(key));
    inflight.set(key, request);
  }
  return request as Promise<T>;
}

const useOwnerRevalidation = create<{ tick: number }>(() => ({ tick: 0 }));

let invalidatedAt = 0;

export function invalidateOwner(): void {
  const now = Date.now();
  if (now - invalidatedAt < CACHE_TTL_MS) return;
  invalidatedAt = now;
  cache.clear();
  useOwnerRevalidation.setState((s) => ({ tick: s.tick + 1 }));
}

function fetchProvider(pubkey: string): Promise<ProviderPayload> {
  return cached(`p|${pubkey}`, () => backend.provider(pubkey));
}

function fetchStats(pubkey: string, period: OwnerPeriod): Promise<StatsPayload> {
  const api = OWNER_PERIOD_API[period];
  return cached(`s|${pubkey}|${api}`, () => backend.providerStats(pubkey, api));
}

function fetchChart(pubkey: string, range: OwnerChartRange): Promise<ChartPayload> {
  return cached(`c|${pubkey}|${range}`, () => backend.providerChart(pubkey, range));
}

const PREFETCH_PERIODS: OwnerPeriod[] = ["hour", "week", "month"];
const DEFAULT_CHART_RANGE: OwnerChartRange = "1h";

export function prefetchOwner(pubkey: string): void {
  if (!useAuth.getState().token) return;
  fetchProvider(pubkey).catch(() => {});
  fetchChart(pubkey, DEFAULT_CHART_RANGE).catch(() => {});
  for (const period of PREFETCH_PERIODS) {
    fetchStats(pubkey, period).catch(() => {});
  }
}

async function composedOwner(
  pubkey: string,
  period: OwnerPeriod,
  chartRange: OwnerChartRange,
): Promise<OwnerPayload> {
  const [provider, stats, chart] = await Promise.all([
    fetchProvider(pubkey),
    fetchStats(pubkey, period),
    fetchChart(pubkey, chartRange),
  ]);
  return { ...provider, summary: stats.summary, chart: chart.points };
}

export function useOwnerData(
  pubkey: string,
  enabled: boolean,
  period: OwnerPeriod,
  chartRange: OwnerChartRange = DEFAULT_CHART_RANGE,
): { payload: OwnerPayload | null; denied: boolean; failed: boolean; refreshing: boolean } {
  const token = useAuth((s) => s.token);
  const tick = useOwnerRevalidation((s) => s.tick);
  const [payload, setPayload] = useState<OwnerPayload | null>(null);
  const [denied, setDenied] = useState(false);
  const [failed, setFailed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const params = useRef("");

  useEffect(() => {
    if (!enabled || !token) {
      setPayload(null);
      setDenied(false);
      setFailed(false);
      setRefreshing(false);
      return;
    }
    const key = `${pubkey}:${period}:${chartRange}`;
    if (params.current !== key) {
      params.current = key;
      setRefreshing(true);
    }
    let alive = true;
    composedOwner(pubkey, period, chartRange)
      .then((data) => {
        if (!alive) return;
        setPayload(data);
        setFailed(false);
        setRefreshing(false);
      })
      .catch((error: unknown) => {
        if (!alive) return;
        setRefreshing(false);
        if (error instanceof BackendError && error.detail === "Banned") useAuth.getState().setBanned(true);
        else if (error instanceof BackendError && error.status === 403) setDenied(true);
        else {
          setFailed(true);
          console.error("owner data failed", error);
        }
      });
    return () => {
      alive = false;
    };
  }, [pubkey, enabled, token, period, chartRange, tick]);

  return { payload, denied, failed, refreshing };
}

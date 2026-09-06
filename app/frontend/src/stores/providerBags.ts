import { backend, type Bag, type BagFilter } from "@/data/backend";
import { create } from "zustand";

// Same freshness the catalogue keeps, so a return from a bag costs no request at all.
const STALE_MS = 120_000;

interface Bucket {
  items: Bag[];
  total: number;
  fetchedAt: number;
}

interface ProviderBagsState {
  buckets: Record<string, Bucket>;
  load: (pubkey: string, state: BagFilter) => Promise<void>;
}

export function bucketKey(pubkey: string, state: BagFilter): string {
  return `${pubkey}|${state}`;
}

export const useProviderBags = create<ProviderBagsState>((set, get) => ({
  buckets: {},
  load: async (pubkey, state) => {
    const key = bucketKey(pubkey, state);
    const cached = get().buckets[key];
    if (cached && Date.now() - cached.fetchedAt < STALE_MS) return;
    const { items, total } = await backend.providerBags(pubkey, state);
    set((s) => ({ buckets: { ...s.buckets, [key]: { items, total, fetchedAt: Date.now() } } }));
  },
}));

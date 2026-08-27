import { cloudStorage } from "@tma.js/sdk-react";
import { createJSONStorage, type PersistOptions, type StateStorage } from "zustand/middleware";
import { isInTelegram } from "./telegram";

const CLOUD_TIMEOUT_MS = 2000;

const dirtyStores = new Set<string>();

function markStoreDirty(name: string): void {
  dirtyStores.add(name);
}

async function cloudGet(name: string): Promise<string | null> {
  try {
    if (!cloudStorage.getItem.isAvailable()) return null;
    const value = await cloudStorage.getItem(name, { timeout: CLOUD_TIMEOUT_MS });
    return value || null;
  } catch {
    return null;
  }
}

async function cloudSet(name: string, value: string): Promise<void> {
  if (cloudStorage.setItem.isAvailable()) {
    await cloudStorage.setItem(name, value, { timeout: CLOUD_TIMEOUT_MS });
  }
}

async function cloudRemove(name: string): Promise<void> {
  if (cloudStorage.deleteItem.isAvailable()) {
    await cloudStorage.deleteItem(name, { timeout: CLOUD_TIMEOUT_MS });
  }
}

const writeChains = new Map<string, Promise<void>>();

function enqueueWrite(name: string, task: () => Promise<void>): void {
  const run = () =>
    task().catch((error: unknown) => console.warn(`Cloud write for "${name}" failed`, error));
  const next = (writeChains.get(name) ?? Promise.resolve()).then(run);
  writeChains.set(name, next);
}

const appStorage: StateStorage = {
  getItem: (name) => (isInTelegram() ? cloudGet(name) : localStorage.getItem(name)),
  setItem: (name, value) => {
    if (isInTelegram()) enqueueWrite(name, () => cloudSet(name, value));
    else localStorage.setItem(name, value);
  },
  removeItem: (name) => {
    if (isInTelegram()) enqueueWrite(name, () => cloudRemove(name));
    else localStorage.removeItem(name);
  },
};

type AppPersistOptions<S> = Pick<PersistOptions<S, S>, "name" | "storage" | "skipHydration" | "merge">;

export function appPersist<S extends object>(name: string): AppPersistOptions<S> {
  return {
    name,
    storage: createJSONStorage<S>(() => appStorage),
    skipHydration: true,
    merge: (persisted, current) =>
      dirtyStores.has(name) ? current : { ...current, ...(persisted as Partial<S>) },
  };
}

interface PersistedStore {
  subscribe: (listener: () => void) => () => void;
  persist: {
    getOptions: () => { name?: string };
    rehydrate: () => unknown;
  };
}

const hydrationListeners = new Set<() => void>();

let hydrated = false;

export function isHydrated(): boolean {
  return hydrated;
}

export function onHydrated(listener: () => void): () => void {
  hydrationListeners.add(listener);
  return () => {
    hydrationListeners.delete(listener);
  };
}

export async function hydrateStores(stores: PersistedStore[]): Promise<void> {
  const unsubscribers = stores.map((store) => {
    const name = store.persist.getOptions().name ?? "";
    return store.subscribe(() => markStoreDirty(name));
  });
  await Promise.all(stores.map((store) => Promise.resolve(store.persist.rehydrate()).catch(() => {})));
  unsubscribers.forEach((unsubscribe) => unsubscribe());
  hydrated = true;
  hydrationListeners.forEach((listener) => listener());
}

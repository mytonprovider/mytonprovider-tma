import { appPersist } from "@/lib/storage";
import { create } from "zustand";
import { persist } from "zustand/middleware";

type NameMap = Record<string, string>;

interface NamesState {
  providers: NameMap;
  addresses: NameMap;
  setProvider: (pubkey: string, name: string) => void;
  setAddress: (address: string, name: string) => void;
  setAll: (providers: NameMap, addresses: NameMap) => void;
}

function assign(map: NameMap, key: string, name: string): NameMap {
  const next = { ...map };
  if (name) next[key] = name;
  else delete next[key];
  return next;
}

export const useNames = create<NamesState>()(
  persist(
    (set) => ({
      providers: {},
      addresses: {},
      setProvider: (pubkey, name) => set((state) => ({ providers: assign(state.providers, pubkey, name) })),
      setAddress: (address, name) => set((state) => ({ addresses: assign(state.addresses, address, name) })),
      setAll: (providers, addresses) => set({ providers, addresses }),
    }),
    appPersist("mtp-names"),
  ),
);

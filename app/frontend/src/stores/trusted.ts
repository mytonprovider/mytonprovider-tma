import { appPersist } from "@/lib/storage";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface TrustedState {
  addresses: string[];
  toggle: (address: string) => void;
  setAll: (addresses: string[]) => void;
}

export const useTrusted = create<TrustedState>()(
  persist(
    (set) => ({
      addresses: [],
      toggle: (address) =>
        set((state) => ({
          addresses: state.addresses.includes(address)
            ? state.addresses.filter((a) => a !== address)
            : [...state.addresses, address],
        })),
      setAll: (addresses) => set({ addresses }),
    }),
    appPersist("mtp-trusted"),
  ),
);

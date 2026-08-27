import { appPersist } from "@/lib/storage";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SubscriptionsState {
  subscribed: string[];
  alertsOff: string[];
  subscribe: (pubkey: string) => void;
  unsubscribe: (pubkey: string) => void;
  toggleAlert: (pubkey: string) => void;
  setAll: (entries: { pubkey: string; alertsEnabled: boolean }[]) => void;
}

export const useSubscriptions = create<SubscriptionsState>()(
  persist(
    (set) => ({
      subscribed: [],
      alertsOff: [],
      subscribe: (pubkey) =>
        set((state) =>
          state.subscribed.includes(pubkey) ? state : { subscribed: [...state.subscribed, pubkey] },
        ),
      unsubscribe: (pubkey) =>
        set((state) => ({
          subscribed: state.subscribed.filter((p) => p !== pubkey),
          alertsOff: state.alertsOff.filter((p) => p !== pubkey),
        })),
      toggleAlert: (pubkey) =>
        set((state) => ({
          alertsOff: state.alertsOff.includes(pubkey)
            ? state.alertsOff.filter((p) => p !== pubkey)
            : [...state.alertsOff, pubkey],
        })),
      setAll: (entries) =>
        set({
          subscribed: entries.map((e) => e.pubkey),
          alertsOff: entries.filter((e) => !e.alertsEnabled).map((e) => e.pubkey),
        }),
    }),
    appPersist("mtp-subscriptions"),
  ),
);

import { appPersist } from "@/lib/storage";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FavoritesState {
  favorites: string[];
  toggle: (pubkey: string) => void;
  setAll: (favorites: string[]) => void;
}

export const useFavorites = create<FavoritesState>()(
  persist(
    (set) => ({
      favorites: [],
      toggle: (pubkey) =>
        set((state) => ({
          favorites: state.favorites.includes(pubkey)
            ? state.favorites.filter((p) => p !== pubkey)
            : [...state.favorites, pubkey],
        })),
      setAll: (favorites) => set({ favorites }),
    }),
    appPersist("mtp-favorites"),
  ),
);

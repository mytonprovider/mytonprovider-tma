import type { Lang } from "@/i18n/types";
import { appPersist } from "@/lib/storage";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "dark" | "light";
export type Explorer = "tonviewer" | "tonscan";

interface SettingsState {
  theme: Theme;
  themeAuto: boolean;
  lang: Lang;
  langAuto: boolean;
  explorer: Explorer;
  setTheme: (theme: Theme) => void;
  setLang: (lang: Lang) => void;
  setExplorer: (explorer: Explorer) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "dark",
      themeAuto: true,
      lang: "en",
      langAuto: true,
      explorer: "tonviewer",
      setTheme: (theme) => set({ theme, themeAuto: false }),
      setLang: (lang) => set({ lang, langAuto: false }),
      setExplorer: (explorer) => set({ explorer }),
    }),
    appPersist("mtp-settings"),
  ),
);

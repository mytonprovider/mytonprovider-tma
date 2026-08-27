import { isInTelegram } from "@/lib/telegram";
import { type Theme, useSettings } from "@/stores/settings";
import { miniApp, useSignal } from "@tma.js/sdk-react";
import { useEffect, useState } from "react";

const LIGHT_QUERY = "(prefers-color-scheme: light)";

function useColorScheme(): Theme {
  const [scheme, setScheme] = useState<Theme>(() =>
    window.matchMedia(LIGHT_QUERY).matches ? "light" : "dark",
  );

  useEffect(() => {
    const query = window.matchMedia(LIGHT_QUERY);
    const handler = (event: MediaQueryListEvent) => setScheme(event.matches ? "light" : "dark");
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  return scheme;
}

export function useAppliedTheme(): Theme {
  const theme = useSettings((state) => state.theme);
  const themeAuto = useSettings((state) => state.themeAuto);
  const browserScheme = useColorScheme();
  const telegramDark = useSignal(miniApp.isDark);

  if (!themeAuto) return theme;
  if (isInTelegram()) return telegramDark ? "dark" : "light";
  return browserScheme;
}

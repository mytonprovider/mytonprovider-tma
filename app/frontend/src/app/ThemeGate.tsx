import { useAppliedTheme } from "@/hooks/useTheme";
import { isInTelegram } from "@/lib/telegram";
import { miniApp } from "@tma.js/sdk-react";
import { type ReactNode, useLayoutEffect, useRef } from "react";

function paintTelegramBands(): void {
  if (!isInTelegram()) return;
  const color = getComputedStyle(document.documentElement).getPropertyValue("--ts-bg").trim();
  if (!color.startsWith("#")) return;
  try {
    miniApp.setBgColor.ifAvailable(color);
    if (miniApp.setHeaderColor.supports("rgb")) miniApp.setHeaderColor.ifAvailable(color);
    miniApp.setBottomBarColor.ifAvailable(color);
  } catch {}
}

export function ThemeGate({ children }: { children: ReactNode }) {
  const theme = useAppliedTheme();
  const painted = useRef(false);

  useLayoutEffect(() => {
    const apply = () => {
      document.documentElement.dataset.theme = theme;
      paintTelegramBands();
    };
    const start = document.startViewTransition?.bind(document);
    if (painted.current && start) start(apply);
    else apply();
    painted.current = true;
  }, [theme]);

  return <>{children}</>;
}

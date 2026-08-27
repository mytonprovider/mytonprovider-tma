import { ErrorBoundary } from "@/components/ErrorBoundary";
import { HashRouter } from "react-router-dom";
import { endSession } from "@/app/session";
import { Callout } from "@/components/Callout";
import { useT } from "@/i18n";
import { useAuth } from "@/stores/auth";
import { AppShell } from "./AppShell";
import { AppRoutes } from "./routes";
import { ThemeGate } from "./ThemeGate";
import styles from "./Root.module.css";

export function Root() {
  const banned = useAuth((state) => state.banned);
  const t = useT();
  return (
    <ErrorBoundary
      fallback={() => (
        <Callout desc={t.loadError}>
          <button type="button" className={styles.logout} onClick={() => location.reload()}>
            {t.retry}
          </button>
        </Callout>
      )}
    >
      <ThemeGate>
        <AppShell>
          {banned ? (
            <Callout glyph="close" title={t.bannedTitle} desc={t.bannedDesc} iconColor="var(--ts-hint)">
              <button type="button" className={styles.logout} onClick={endSession}>
                {t.logout}
              </button>
            </Callout>
          ) : (
            <HashRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
              <AppRoutes />
            </HashRouter>
          )}
        </AppShell>
      </ThemeGate>
    </ErrorBoundary>
  );
}

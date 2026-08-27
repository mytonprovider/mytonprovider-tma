import { InstallBanner } from "@/components/InstallBanner";
import { isInTelegram } from "@/lib/telegram";
import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

export function AppShell({ children }: { children: ReactNode }) {
  if (isInTelegram()) {
    return <div className={styles.viewport}>{children}</div>;
  }
  return (
    <div className={styles.backdrop}>
      <div className={styles.frame}>
        {children}
        <InstallBanner />
      </div>
    </div>
  );
}

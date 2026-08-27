import type { ReactNode } from "react";
import styles from "./BottomBar.module.css";

export function BottomBar({ children }: { children: ReactNode }) {
  return <div className={styles.bar}>{children}</div>;
}

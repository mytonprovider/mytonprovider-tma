import type { ReactNode } from "react";
import styles from "./Screen.module.css";

interface ScreenProps {
  header: ReactNode;
  children: ReactNode;
  bottom?: ReactNode;
}

export function Screen({ header, children, bottom }: ScreenProps) {
  return (
    <div className={styles.screen}>
      {header}
      <div className={styles.scroll}>{children}</div>
      {bottom}
    </div>
  );
}

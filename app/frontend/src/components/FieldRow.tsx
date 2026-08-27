import { cx } from "@/lib/cx";
import type { ReactNode } from "react";
import styles from "./FieldRow.module.css";

interface FieldRowProps {
  label: ReactNode;
  value: ReactNode;
  divider?: boolean;
}

export function FieldRow({ label, value, divider }: FieldRowProps) {
  return (
    <div className={cx(styles.row, divider && styles.divider)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
    </div>
  );
}

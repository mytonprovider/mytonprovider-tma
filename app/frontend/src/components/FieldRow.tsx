import { cx } from "@/lib/cx";
import type { ReactNode } from "react";
import styles from "./FieldRow.module.css";

interface FieldRowProps {
  label: ReactNode;
  value: ReactNode;
  divider?: boolean;
  compact?: boolean;
}

export function FieldRow({ label, value, divider, compact }: FieldRowProps) {
  return (
    <div className={cx(compact ? styles.compact : styles.row, divider && styles.divider)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
    </div>
  );
}

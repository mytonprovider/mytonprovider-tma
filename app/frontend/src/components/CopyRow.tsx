import { CopyButton } from "@/components/CopyButton";
import { cx } from "@/lib/cx";
import type { ReactNode } from "react";
import styles from "./CopyRow.module.css";

export function CopyRow({
  label,
  copyValue,
  divider,
  children,
}: {
  label: string;
  copyValue: string | null;
  divider?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={cx(styles.copyRow, divider && styles.copyRowDivider)}>
      <span className={styles.copyLabel}>{label}</span>
      <span className={styles.copyValue}>
        {children}
        {copyValue && <CopyButton value={copyValue} />}
      </span>
    </div>
  );
}

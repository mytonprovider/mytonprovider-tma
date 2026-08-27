import type { ReactNode } from "react";
import styles from "./MetricTile.module.css";

interface MetricTileProps {
  value: string;
  label: ReactNode;
  unit?: string;
  valueColor?: string;
}

export function MetricTile({ value, label, unit, valueColor }: MetricTileProps) {
  return (
    <div className={styles.tile}>
      <div className={styles.value} style={valueColor ? { color: valueColor } : undefined}>
        {value}
        {unit ? <span className={styles.unit}>{unit}</span> : null}
      </div>
      <div className={styles.label}>{label}</div>
    </div>
  );
}

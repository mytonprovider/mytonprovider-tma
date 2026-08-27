import styles from "./StatusDot.module.css";

interface StatusDotProps {
  color: string;
  size: number;
}

export function StatusDot({ color, size }: StatusDotProps) {
  return <span className={styles.dot} style={{ width: size, height: size, background: color }} />;
}

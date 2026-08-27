import { cx } from "@/lib/cx";
import type { ReactNode } from "react";
import styles from "./Card.module.css";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <div className={cx(styles.card, className)}>{children}</div>;
}

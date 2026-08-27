import { Icon } from "@/components/Icon/Icon";
import { useInSheet } from "@/app/layers/Sheet";
import { bindBackButton, isInTelegram } from "@/lib/telegram";
import { type ReactNode, useEffect, useRef } from "react";
import styles from "./ScreenHeader.module.css";

interface ScreenHeaderProps {
  title: ReactNode;
  onBack: () => void;
  right?: ReactNode;
}

export function ScreenHeader({ title, onBack, right }: ScreenHeaderProps) {
  const handler = useRef(onBack);
  handler.current = onBack;
  const inSheet = useInSheet();

  useEffect(() => bindBackButton(() => handler.current()), []);

  return (
    <header className={styles.header}>
      {!isInTelegram() && !inSheet && (
        <button type="button" aria-label="Back" className={styles.back} onClick={onBack}>
          <Icon glyph="arrowLeft" size={23} color="var(--ts-accent)" />
        </button>
      )}
      <div className={styles.title}>{title}</div>
      {right && <div className={styles.right}>{right}</div>}
    </header>
  );
}

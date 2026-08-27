import { tick } from "@/lib/telegram";
import { Icon } from "@/components/Icon/Icon";
import { SC } from "@/lib/colors";
import { cx } from "@/lib/cx";
import { type MouseEvent, useRef, useState } from "react";
import styles from "./CopyButton.module.css";

interface CopyButtonProps {
  value: string;
  className?: string;
}

export function CopyButton({ value, className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const onClick = (event: MouseEvent<HTMLButtonElement>) => {
    tick();
    event.stopPropagation();
    void navigator.clipboard?.writeText(value);
    setCopied(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 1300);
  };

  return (
    <button type="button" aria-label="Copy" className={cx(styles.button, className)} onClick={onClick}>
      {copied ? (
        <Icon glyph="check" size={16} color={SC.green} stroke={2.6} />
      ) : (
        <Icon glyph="copy" size={15} color="var(--ts-accent)" stroke={2} />
      )}
    </button>
  );
}

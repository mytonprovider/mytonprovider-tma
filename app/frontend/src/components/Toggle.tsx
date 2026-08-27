import { tick } from "@/lib/telegram";
import { cx } from "@/lib/cx";
import styles from "./Toggle.module.css";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  ariaLabel?: string;
}

export function Toggle({ checked, onChange, ariaLabel }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      className={cx(styles.track, checked && styles.on)}
      onClick={() => {
        tick();
        onChange(!checked);
      }}
    >
      <span className={styles.knob} />
    </button>
  );
}

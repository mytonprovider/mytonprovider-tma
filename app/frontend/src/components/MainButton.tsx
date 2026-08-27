import { Icon } from "@/components/Icon/Icon";
import { cx } from "@/lib/cx";
import styles from "./MainButton.module.css";

type MainButtonTone = "accent" | "destructive";
type MainButtonState = "idle" | "loading" | "success";

interface MainButtonProps {
  label: string;
  tone?: MainButtonTone;
  state?: MainButtonState;
  disabled?: boolean;
  onClick?: () => void;
}

export function MainButton({
  label,
  tone = "accent",
  state = "idle",
  disabled = false,
  onClick,
}: MainButtonProps) {
  const busy = state === "loading" || state === "success";
  const idleDisabled = disabled && !busy;
  const clickable = !idleDisabled && !busy;

  const className = cx(
    styles.button,
    state === "success" && styles.success,
    idleDisabled && styles.disabled,
    !idleDisabled && state !== "success" && tone === "destructive" && styles.destructive,
    !clickable && styles.static,
  );

  return (
    <button
      type="button"
      className={className}
      onClick={clickable ? onClick : undefined}
      disabled={idleDisabled}
    >
      {state === "loading" && <span className={styles.spinner} />}
      {state === "success" && <Icon glyph="check" size={20} color="#fff" />}
      {state === "idle" && <span>{label}</span>}
    </button>
  );
}

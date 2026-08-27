import { tick } from "@/lib/telegram";
import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import { ACCENT } from "@/lib/colors";
import type { MouseEvent } from "react";
import styles from "./RoundToggle.module.css";

interface RoundToggleProps {
  glyph: GlyphName;
  active: boolean;
  ariaLabel: string;
  onClick: (event: MouseEvent<HTMLButtonElement>) => void;
  size?: number;
}

export function RoundToggle({ glyph, active, ariaLabel, onClick, size = 18 }: RoundToggleProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className={styles.button}
      onClick={(event) => {
        tick();
        onClick(event);
      }}
    >
      <Icon
        glyph={glyph}
        size={size}
        fill={active ? ACCENT : "none"}
        strokeColor={active ? ACCENT : "var(--ts-hint)"}
      />
    </button>
  );
}

import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import { cx } from "@/lib/cx";
import type { ReactNode } from "react";
import styles from "./Callout.module.css";

interface CalloutProps {
  hero?: boolean;
  glyph?: GlyphName;
  icon?: ReactNode;
  iconColor?: string;
  title?: string;
  desc?: ReactNode;
  children?: ReactNode;
}

export function Callout({ hero, glyph, icon, iconColor = "var(--ts-accent)", title, desc, children }: CalloutProps) {
  const disc = hero && !icon;
  const mark = icon ?? (glyph ? <Icon glyph={glyph} size={disc ? 19 : 42} color={disc ? "#fff" : iconColor} filled={disc} /> : null);

  return (
    <div className={cx(styles.root, hero && styles.hero)}>
      {mark ? (
        <span className={cx(styles.mark, disc && styles.disc)} style={disc ? { background: iconColor } : undefined}>
          {mark}
        </span>
      ) : null}
      {title ? <div className={styles.title}>{title}</div> : null}
      {desc ? <div className={styles.desc}>{desc}</div> : null}
      {children ? <div className={styles.action}>{children}</div> : null}
    </div>
  );
}

import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import styles from "./SectionHeader.module.css";

interface SectionHeaderProps {
  glyph?: GlyphName;
  title: string;
}

export function SectionHeader({ glyph, title }: SectionHeaderProps) {
  return (
    <div className={styles.header}>
      {glyph && <Icon glyph={glyph} size={14} />}
      <span>{title}</span>
    </div>
  );
}

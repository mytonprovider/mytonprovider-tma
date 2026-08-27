import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import { cx } from "@/lib/cx";
import { tick } from "@/lib/telegram";
import { useSegmentDrag } from "@/hooks/useSegmentDrag";
import { type KeyboardEvent, type ReactNode, useEffect, useRef } from "react";
import styles from "./FloatingTabs.module.css";

const DOCK_SPACE = "74px";

interface FloatingTab<T extends string> {
  key: T;
  label: string;
  glyph?: GlyphName;
  icon?: (active: boolean) => ReactNode;
}

interface FloatingTabsProps<T extends string> {
  tabs: readonly FloatingTab<T>[];
  tab: T;
  progress: number;
  onSelect: (tab: T) => void;
  onScrub: (position: number | null) => void;
}

export function FloatingTabs<T extends string>({ tabs, tab, progress, onSelect, onScrub }: FloatingTabsProps<T>) {
  const barRef = useRef<HTMLDivElement>(null);
  const activeIndex = Math.max(
    0,
    tabs.findIndex((item) => item.key === tab),
  );
  const thumb = Math.min(Math.max(progress, 0), tabs.length - 1);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--ts-dock-space", DOCK_SPACE);
    return () => {
      root.style.removeProperty("--ts-dock-space");
    };
  }, []);

  const select = (next: T) => {
    if (next !== tab) tick();
    onSelect(next);
  };

  const { offset, handlers } = useSegmentDrag(
    barRef,
    tabs.length,
    activeIndex,
    (index) => {
      const next = tabs[index];
      if (next) select(next.key);
    },
    onScrub,
  );

  const nearest = offset === null ? Math.round(thumb) : activeIndex;

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = tabs[Math.min(Math.max(activeIndex + step, 0), tabs.length - 1)];
    if (!next) return;
    select(next.key);
    document.getElementById(`tab-${next.key}`)?.focus();
  };

  return (
    <div className={styles.dock}>
      <div
        ref={barRef}
        className={styles.bar}
        role="tablist"
        aria-orientation="horizontal"
        onKeyDown={onKeyDown}
        {...handlers}
      >
        <span
          className={cx(styles.thumb, offset !== null && styles.thumbHeld)}
          style={{
            width: `calc((100% - 8px) / ${tabs.length})`,
            transform: offset === null ? `translateX(${thumb * 100}%)` : `translateX(${offset}px)`,
          }}
        />
        {tabs.map((item, index) => {
          const active = item.key === tab;
          const lit = index === nearest;
          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              id={`tab-${item.key}`}
              aria-controls={`pane-${item.key}`}
              aria-selected={active}
              tabIndex={active ? 0 : -1}
              className={cx(styles.tab, lit && styles.active)}
              onClick={() => select(item.key)}
            >
              {item.icon ? item.icon(lit) : item.glyph && <Icon glyph={item.glyph} size={22} filled={lit} />}
              <span className={styles.label}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

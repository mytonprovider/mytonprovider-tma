import { reducedMotion } from "@/lib/motion";
import { type MutableRefObject, type ReactNode, type UIEvent, useEffect, useLayoutEffect, useRef } from "react";
import styles from "./TabPager.module.css";

const SETTLE_MS = 140;

interface TabPagerProps<T extends string> {
  tabs: readonly T[];
  tab: T;
  scrubRef?: MutableRefObject<(position: number | null) => void>;
  panes: MutableRefObject<Record<string, HTMLDivElement | null>>;
  onTabChange: (tab: T) => void;
  onProgress?: (progress: number) => void;
  onPaneScroll?: (tab: T, scrollTop: number) => void;
  children: (tab: T) => ReactNode;
}

export function TabPager<T extends string>({
  tabs,
  tab,
  scrubRef,
  panes,
  onTabChange,
  onProgress,
  onPaneScroll,
  children,
}: TabPagerProps<T>) {
  const trackRef = useRef<HTMLDivElement>(null);
  const settleTimer = useRef<ReturnType<typeof setTimeout>>();
  const settleRef = useRef<() => void>(() => {});
  const dragging = useRef(false);
  const ready = useRef(false);
  const indexRef = useRef(0);
  const scrubbing = useRef(false);

  useEffect(() => () => clearTimeout(settleTimer.current), []);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const handler = () => settleRef.current();
    track.addEventListener("scrollend", handler);
    return () => track.removeEventListener("scrollend", handler);
  }, []);

  useLayoutEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const index = tabs.indexOf(tab);
    if (index >= 0) indexRef.current = index;
    if (scrubbing.current || index < 0) return;
    const instant = !ready.current || dragging.current || reducedMotion();
    ready.current = true;
    const target = index * track.clientWidth;
    if (Math.abs(track.scrollLeft - target) < 1) {
      track.style.scrollSnapType = "";
      return;
    }
    track.scrollTo({ left: target, behavior: instant ? "auto" : "smooth" });
  }, [tab, tabs]);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    let width = track.clientWidth;
    const observer = new ResizeObserver(() => {
      if (track.clientWidth === width) return;
      width = track.clientWidth;
      track.scrollLeft = indexRef.current * width;
    });
    observer.observe(track);
    return () => observer.disconnect();
  }, []);

  const scrub = (position: number | null) => {
    if (position === null) scrubbing.current = false;
    const track = trackRef.current;
    if (!track || !track.clientWidth) return;
    if (position === null) {
      track.style.scrollSnapType = "";
      const index = Math.round(track.scrollLeft / track.clientWidth);
      track.scrollTo({ left: index * track.clientWidth, behavior: reducedMotion() ? "auto" : "smooth" });
      return;
    }
    scrubbing.current = true;
    track.style.scrollSnapType = "none";
    track.scrollLeft = position * track.clientWidth;
  };

  const settle = () => {
    const track = trackRef.current;
    if (!track || !track.clientWidth || scrubbing.current) return;
    track.style.scrollSnapType = "";
    dragging.current = false;
    const index = Math.min(Math.max(Math.round(track.scrollLeft / track.clientWidth), 0), tabs.length - 1);
    const target = index * track.clientWidth;
    if (Math.abs(track.scrollLeft - target) >= 1) track.scrollLeft = target;
    const next = tabs[index];
    if (next && next !== tab) onTabChange(next);
  };

  settleRef.current = settle;
  if (scrubRef) scrubRef.current = scrub;

  const onScroll = (event: UIEvent<HTMLDivElement>) => {
    const track = event.currentTarget;
    if (!track.clientWidth) return;
    onProgress?.(track.scrollLeft / track.clientWidth);
    clearTimeout(settleTimer.current);
    settleTimer.current = setTimeout(settle, SETTLE_MS);
  };

  return (
    <div
      ref={trackRef}
      className={styles.track}
      data-no-drag
      onScroll={onScroll}
      onPointerDown={() => {
        dragging.current = true;
      }}
      onPointerUp={() => {
        dragging.current = false;
      }}
      onPointerCancel={() => {
        dragging.current = false;
      }}
    >
      {tabs.map((key) => (
        <div
          key={key}
          ref={(element) => {
            panes.current[key] = element;
          }}
          className={styles.pane}
          role="tabpanel"
          id={`pane-${key}`}
          aria-labelledby={`tab-${key}`}
          onScroll={(event) => onPaneScroll?.(key, event.currentTarget.scrollTop)}
        >
          <div className={styles.inner}>{children(key)}</div>
        </div>
      ))}
    </div>
  );
}

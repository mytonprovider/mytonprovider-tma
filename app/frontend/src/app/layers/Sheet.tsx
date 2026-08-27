import { cx } from "@/lib/cx";
import { reducedMotion } from "@/lib/motion";
import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from "react";
import styles from "./Sheet.module.css";
import type { SheetHeight } from "./presentation";
import { useSheetDrag } from "./useSheetDrag";

const OPEN_MS = 420;
const CLOSE_MS = 260;
const CLOSE_EASE = "cubic-bezier(0.32, 0.72, 0, 1)";

const SheetContext = createContext(false);

export function useInSheet(): boolean {
  return useContext(SheetContext);
}

interface SheetProps {
  height: SheetHeight;
  depth: number;
  top: boolean;
  closing: boolean;
  title?: string;
  subtitle?: ReactNode;
  onDismiss: () => void;
  onClosed: () => void;
  children: ReactNode;
}

export function Sheet({ height, depth, top, closing, title, subtitle, onDismiss, onClosed, children }: SheetProps) {
  const layerRef = useRef<HTMLDivElement>(null);
  const scrimRef = useRef<HTMLDivElement>(null);
  const grabberRef = useRef<HTMLButtonElement>(null);
  const { ref: dragRef, element: sheetRef, offset, dragging, handlers } = useSheetDrag(top && !closing, onDismiss);

  useEffect(() => {
    const layer = layerRef.current;
    if (layer) layer.inert = !top;
  }, [top]);

  const [entering, setEntering] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setEntering(false), OPEN_MS);
    return () => clearTimeout(timer);
  }, []);

  const opener = useRef<Element | null>(null);
  opener.current ??= document.activeElement;

  useEffect(() => {
    grabberRef.current?.focus({ preventScroll: true });
    return () => {
      const previous = opener.current;
      requestAnimationFrame(() => {
        if (previous instanceof HTMLElement && document.contains(previous)) previous.focus({ preventScroll: true });
      });
    };
  }, []);

  const closed = useRef(onClosed);
  closed.current = onClosed;

  useEffect(() => {
    const sheet = sheetRef.current;
    if (!closing || !sheet) return;
    const from = getComputedStyle(sheet).transform;
    const duration = reducedMotion() ? 0 : CLOSE_MS;
    const slide = sheet.animate([{ transform: from === "none" ? "translateY(0px)" : from }, { transform: "translateY(100%)" }], {
      duration,
      easing: CLOSE_EASE,
      fill: "forwards",
    });
    const scrim = scrimRef.current;
    if (scrim) {
      scrim.animate([{ opacity: getComputedStyle(scrim).opacity }, { opacity: 0 }], {
        duration,
        easing: CLOSE_EASE,
        fill: "forwards",
      });
    }
    const finish = () => closed.current();
    slide.addEventListener("finish", finish);
    const timer = setTimeout(finish, CLOSE_MS * 2);
    return () => {
      slide.removeEventListener("finish", finish);
      clearTimeout(timer);
    };
  }, [closing]);

  return (
    <div
      ref={layerRef}
      className={styles.layer}
      style={{ ["--layer-depth" as string]: depth }}
      role="dialog"
      aria-modal={top}
      aria-label={title}
    >
      <div ref={scrimRef} className={styles.scrim} onClick={top && !closing ? onDismiss : undefined} />
      <div
        ref={dragRef}
        className={cx(
          styles.sheet,
          styles[height],
          entering && styles.entering,
          dragging && styles.dragging,
          !closing && !top && styles.behind,
        )}
        style={offset > 0 ? { transform: `translateY(${offset}px)` } : undefined}
        {...handlers}
      >
        <button ref={grabberRef} type="button" className={styles.grabber} aria-label="Close" onClick={onDismiss} />
        {title && <div className={styles.title}>{title}</div>}
        {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
        <SheetContext.Provider value>
          <div className={styles.body}>{children}</div>
        </SheetContext.Provider>
      </div>
    </div>
  );
}

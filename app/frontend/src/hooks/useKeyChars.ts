import { type RefObject, useLayoutEffect, useState } from "react";

const units = new Map<string, number>();

function unitWidth(element: HTMLElement): number {
  const style = getComputedStyle(element);
  const key = `${style.font} ${style.letterSpacing}`;
  const known = units.get(key);
  if (known) return known;
  const probe = document.createElement("span");
  probe.style.cssText = `position:absolute;visibility:hidden;white-space:pre;font:${style.font};letter-spacing:${style.letterSpacing}`;
  probe.textContent = "0000000000";
  document.body.appendChild(probe);
  const unit = probe.getBoundingClientRect().width / 10;
  probe.remove();
  if (unit > 0) units.set(key, unit);
  return unit;
}

export function useKeyChars(rowRef: RefObject<HTMLElement>, keyRef: RefObject<HTMLElement>, max: number): number {
  const [chars, setChars] = useState(max);

  useLayoutEffect(() => {
    const row = rowRef.current;
    const key = keyRef.current;
    if (!row || !key) return;
    const measure = () => {
      const unit = unitWidth(key);
      if (!unit || !row.clientWidth) return;
      const gap = parseFloat(getComputedStyle(row).columnGap) || 0;
      let taken = 0;
      for (const child of row.children) {
        if (child !== key) taken += child.getBoundingClientRect().width + gap;
      }
      setChars(Math.max(1, Math.min(max, Math.floor((row.clientWidth - taken) / unit))));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(row);
    return () => observer.disconnect();
  }, [rowRef, keyRef, max]);

  return chars;
}

import type { Range } from "@/data/types";
import { useSliderDrag } from "@/hooks/useSliderDrag";
import { useRef } from "react";
import styles from "./RangeSlider.module.css";

interface RangeSliderProps {
  value: Range;
  min: number;
  max: number;
  step: number;
  onChange: (value: Range) => void;
}

export function RangeSlider({ value, min, max, step, onChange }: RangeSliderProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const span = max - min || 1;
  const [lo, hi] = value;
  const loPct = ((lo - min) / span) * 100;
  const hiPct = ((hi - min) / span) * 100;

  const snap = (ratio: number) => {
    const snapped = Math.round((min + ratio * span) / step) * step;
    return Math.max(min, Math.min(max, snapped));
  };
  const onLoDown = useSliderDrag(trackRef, (ratio) => onChange([Math.min(snap(ratio), hi), hi]));
  const onHiDown = useSliderDrag(trackRef, (ratio) => onChange([lo, Math.max(snap(ratio), lo)]));

  return (
    <div className={styles.wrap}>
      <div className={styles.track} ref={trackRef} data-no-drag>
        <div className={styles.fill} style={{ left: `${loPct}%`, width: `${hiPct - loPct}%` }} />
        <div className={styles.thumb} style={{ left: `${loPct}%` }} onPointerDown={onLoDown} />
        <div className={styles.thumb} style={{ left: `${hiPct}%` }} onPointerDown={onHiDown} />
      </div>
    </div>
  );
}

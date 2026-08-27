import { THRESHOLD_MAX, THRESHOLD_MIN } from "@/data/alerts";
import { useSliderDrag } from "@/hooks/useSliderDrag";
import { useRef } from "react";
import styles from "./ThresholdSlider.module.css";

const RANGE = THRESHOLD_MAX - THRESHOLD_MIN;

interface ThresholdSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export function ThresholdSlider({ value, onChange }: ThresholdSliderProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const pct = ((value - THRESHOLD_MIN) / RANGE) * 100;
  const onDown = useSliderDrag(trackRef, (ratio) => onChange(Math.round(THRESHOLD_MIN + ratio * RANGE)));

  return (
    <div className={styles.row}>
      <div className={styles.area}>
        <div className={styles.track} ref={trackRef} data-no-drag>
          <div className={styles.fill} style={{ width: `${pct}%` }} />
          <div className={styles.thumb} style={{ left: `${pct}%` }} onPointerDown={onDown} />
        </div>
      </div>
      <span className={styles.value}>≥ {value}%</span>
    </div>
  );
}

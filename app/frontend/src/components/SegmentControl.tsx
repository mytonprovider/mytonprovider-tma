import { tick } from "@/lib/telegram";
import { cx } from "@/lib/cx";
import { useSegmentDrag } from "@/hooks/useSegmentDrag";
import { useRef } from "react";
import styles from "./SegmentControl.module.css";

interface SegmentOption<T> {
  value: T;
  label: string;
}

interface SegmentControlProps<T> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  height?: number;
  fontSize?: number;
}

export function SegmentControl<T>({
  options,
  value,
  onChange,
  height = 38,
  fontSize = 14,
}: SegmentControlProps<T>) {
  const boxRef = useRef<HTMLDivElement>(null);

  const activeIndex = Math.max(
    0,
    options.findIndex((option) => Object.is(option.value, value)),
  );

  const select = (index: number) => {
    const option = options[index];
    if (!option || Object.is(option.value, value)) return;
    tick();
    onChange(option.value);
  };

  const { offset, handlers } = useSegmentDrag(boxRef, options.length, activeIndex, select);

  return (
    <div
      ref={boxRef}
      className={styles.box}
      style={{ height }}
      role="radiogroup"
      {...handlers}
    >
      <span
        className={cx(styles.thumb, offset !== null && styles.thumbHeld)}
        style={{
          width: `calc((100% - 4px) / ${options.length})`,
          transform: offset === null ? `translateX(${activeIndex * 100}%)` : `translateX(${offset}px)`,
        }}
      />
      {options.map((option, index) => (
        <button
          key={String(option.value)}
          type="button"
          role="radio"
          aria-checked={index === activeIndex}
          className={cx(styles.option, index === activeIndex && styles.active)}
          style={{ fontSize }}
          onClick={() => select(index)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

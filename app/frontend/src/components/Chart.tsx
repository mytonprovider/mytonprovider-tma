import { cx } from "@/lib/cx";
import { tick } from "@/lib/telegram";
import { type PointerEvent as ReactPointerEvent, useId, useRef, useState } from "react";
import styles from "./Chart.module.css";

const WIDTH = 300;
const HEIGHT = 64;
const PAD = 4;
const TWO_DAYS_SEC = 172800;
const BRIDGE_SEC = 300;

interface ChartProps {
  values: (number | null)[];
  peaks: (number | null)[];
  times: number[];
  threshold: number | null;
  unit: string;
  label: string;
  current: string;
  loading?: boolean;
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function timeLabel(unixSec: number, spanSec: number): string {
  const date = new Date(unixSec * 1000);
  const clock = `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
  if (spanSec <= TWO_DAYS_SEC) return clock;
  return `${pad2(date.getDate())}.${pad2(date.getMonth() + 1)} ${clock}`;
}

export function Chart({ values, peaks, times, threshold, unit, label, current, loading }: ChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const clipId = useId();
  const [scrub, setScrub] = useState<number | null>(null);

  const filled: number[] = [];
  values.forEach((value, index) => {
    if (value !== null) filled.push(index);
  });

  if (loading || !filled.length) {
    return (
      <div className={styles.chart}>
        <div className={styles.head}>
          <span className={styles.label}>{label}</span>
          <span className={styles.skelValue} />
        </div>
        <div className={styles.skelBody} />
      </div>
    );
  }

  const count = values.length;
  const value = (index: number) => values[index] as number;
  const peak = (index: number) => peaks[index] ?? value(index);
  const min = Math.min(...filled.map(value));
  const max = Math.max(...filled.map(peak));
  const lo = threshold != null ? Math.min(min, threshold) : min;
  const hi = threshold != null ? Math.max(max, threshold) : max;
  const span = hi - lo || 1;
  const x = (i: number) => PAD + (count > 1 ? (i / (count - 1)) * (WIDTH - 2 * PAD) : (WIDTH - 2 * PAD) / 2);
  const y = (v: number) => HEIGHT - PAD - ((v - lo) / span) * (HEIGHT - 2 * PAD);
  const at = (index: number) => `${x(index).toFixed(1)},${y(value(index)).toFixed(1)}`;
  const atPeak = (index: number) => `${x(index).toFixed(1)},${y(peak(index)).toFixed(1)}`;

  const runs: number[][] = [];
  for (const index of filled) {
    const run = runs[runs.length - 1];
    const previous = run?.[run.length - 1];
    if (previous !== undefined && (index - previous === 1 || times[index] - times[previous] <= BRIDGE_SEC)) run.push(index);
    else runs.push([index]);
  }
  const lines = runs.filter((run) => run.length > 1);
  const dots = runs.filter((run) => run.length === 1).map((run) => run[0]);
  const bridges = filled.slice(1).flatMap((index, position) => {
    const previous = filled[position];
    return index - previous > 1 && times[index] - times[previous] > BRIDGE_SEC ? [[previous, index]] : [];
  });

  const areaPath = lines
    .map((run) => `M${run.map(at).join(" L")} L${x(run[run.length - 1]).toFixed(1)},${HEIGHT} L${x(run[0]).toFixed(1)},${HEIGHT} Z`)
    .join(" ");
  const peakPath = lines.map((run) => `M${run.map(atPeak).join(" L")} L${[...run].reverse().map(at).join(" L")} Z`).join(" ");

  const thresholdY = threshold != null ? y(threshold) : 0;
  const thresholdLine =
    threshold != null
      ? `M${PAD.toFixed(1)},${thresholdY.toFixed(1)} L${(WIDTH - PAD).toFixed(1)},${thresholdY.toFixed(1)}`
      : "";

  const indexFromEvent = (event: ReactPointerEvent<HTMLDivElement>): number | null => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect || count < 2) return null;
    const ratio = (event.clientX - rect.left) / rect.width;
    const target = Math.max(0, Math.min(count - 1, Math.round(ratio * (count - 1))));
    return filled.reduce((best, index) => (Math.abs(index - target) < Math.abs(best - target) ? index : best));
  };

  const moveScrub = (event: ReactPointerEvent<HTMLDivElement>) => {
    const next = indexFromEvent(event);
    if (next !== scrub) {
      if (next !== null) tick();
      setScrub(next);
    }
  };
  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    moveScrub(event);
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (scrub !== null) moveScrub(event);
  };
  const endScrub = () => setScrub(null);

  const spanSec = count > 1 ? times[count - 1] - times[0] : 0;
  const last = filled[filled.length - 1];
  const scrubValue = scrub !== null ? `${value(scrub)}${unit} · ${timeLabel(times[scrub], spanSec)}` : null;

  return (
    <div className={styles.chart}>
      <div className={styles.head}>
        <span className={styles.label}>{label}</span>
        <span className={scrubValue ? styles.scrubValue : styles.current}>{scrubValue ?? current}</span>
      </div>
      <div
        ref={wrapRef}
        className={styles.plot}
        data-no-drag
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endScrub}
        onPointerCancel={endScrub}
      >
        <svg width="100%" height={60} viewBox="0 0 300 64" preserveAspectRatio="none" className={styles.svg}>
          {threshold != null && (
            <defs>
              <clipPath id={`${clipId}-below`}>
                <rect x={0} y={thresholdY} width={WIDTH} height={HEIGHT - thresholdY} />
              </clipPath>
              <clipPath id={`${clipId}-above`}>
                <rect x={0} y={-HEIGHT} width={WIDTH} height={HEIGHT + thresholdY} />
              </clipPath>
            </defs>
          )}
          <path d={peakPath} fill="rgba(0, 152, 234, 0.28)" />
          <path d={areaPath} fill="rgba(0, 152, 234, 0.1)" />
          {thresholdLine && (
            <path d={thresholdLine} fill="none" stroke="#ff3b30" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />
          )}
          {bridges.map(([from, to]) => (
            <path
              key={from}
              d={`M${at(from)} L${at(to)}`}
              fill="none"
              stroke="var(--ts-hint)"
              strokeWidth={1.6}
              strokeDasharray="3 3"
              opacity={0.8}
            />
          ))}
          {lines.map((run) => (
            <polyline
              key={run[0]}
              points={run.map(at).join(" ")}
              fill="none"
              stroke="var(--ts-accent)"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              clipPath={threshold != null ? `url(#${clipId}-below)` : undefined}
            />
          ))}
          {threshold != null &&
            lines.map((run) => (
              <polyline
                key={`over-${run[0]}`}
                points={run.map(at).join(" ")}
                fill="none"
                stroke="#ff3b30"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                clipPath={`url(#${clipId}-above)`}
              />
            ))}
          {dots.map((index) => (
            <circle key={index} cx={x(index)} cy={y(value(index))} r={1.7} fill="var(--ts-accent)" />
          ))}
          {scrub === null && (
            <circle cx={x(last)} cy={y(value(last))} r={3} fill="var(--ts-accent)" stroke="var(--ts-card)" strokeWidth={1.5} />
          )}
          {scrub !== null && (
            <g>
              <line x1={x(scrub)} x2={x(scrub)} y1={0} y2={HEIGHT} stroke="var(--ts-hint)" strokeWidth={1} opacity={0.6} />
              <circle cx={x(scrub)} cy={y(value(scrub))} r={3.5} fill="var(--ts-accent)" stroke="var(--ts-card)" strokeWidth={1.5} />
            </g>
          )}
        </svg>
        {threshold != null && (
          <span
            className={cx(styles.thresholdLabel, thresholdY <= 14 && styles.thresholdLabelBelow)}
            style={{ top: `${(thresholdY / HEIGHT) * 100}%` }}
          >
            {`${threshold}${unit}`}
          </span>
        )}
      </div>
    </div>
  );
}

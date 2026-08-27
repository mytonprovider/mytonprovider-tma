import { useId } from "react";

const DISC =
  "M 234.9589,488.01445 C 184.87522,482.94051 144.8449,466.85693 106.97452,436.59226 97.871178,429.31718 80.569023,411.88329 72.84431,402.20217 39.737916,360.71108 22.291814,311.11923 22.196377,258.23163 22.159053,237.54755 23.9611,222.26091 28.712141,202.95886 41.443448,151.23538 71.816601,105.31181 114.47961,73.28023 184.86865,20.431821 279.4162,12.34084 357.69863,52.46657 c 22.04932,11.301959 39.84795,24.345978 58.03078,42.528807 19.06476,19.064773 32.03559,37.071863 43.86735,60.900013 10.95485,22.06215 17.47468,43.31949 21.31611,69.49938 1.9467,13.26705 2.05874,15.02967 2.0671,32.51806 0.009,19.46263 -0.4966,25.84696 -3.25881,41.12578 -10.94892,60.56282 -46.59911,115.26995 -97.47458,149.57997 -30.96804,20.8846 -62.56447,32.83621 -101.06103,38.22717 -7.01291,0.98207 -39.86942,1.81275 -46.22665,1.1687 z";

interface TonLogoProps {
  size?: number;
  disc?: string;
  mark?: string;
  mono?: boolean;
  filled?: boolean;
}

const MARKS = (
  <>
    <rect width="200" height="35" x="156" y="365.34995" />
    <rect width="257.3848" height="35" x="-266.98523" y="230.39433" transform="rotate(-69.274321)" />
    <rect
      width="257.3848"
      height="35"
      x="-447.58261"
      y="-248.69743"
      transform="matrix(-0.35389406,-0.93528552,-0.93528552,0.35389406,0,0)"
    />
  </>
);

export function TonLogo({ size = 38, disc = "var(--ts-accent)", mark = "#f9f9f9", mono, filled }: TonLogoProps) {
  const id = useId();

  if (mono && !filled) {
    return (
      <svg width={size} height={size} viewBox="22 27 461 461" fill="currentColor">
        <circle cx="252.6" cy="257.7" r="214" fill="none" stroke="currentColor" strokeWidth={32} />
        {MARKS}
      </svg>
    );
  }

  if (mono) {
    return (
      <svg width={size} height={size} viewBox="22 27 461 461" fill="none">
        <mask id={id} fill="#000">
          <path fill="#fff" d={DISC} />
          {MARKS}
        </mask>
        <rect x="22" y="27" width="461" height="461" fill="currentColor" mask={`url(#${id})`} />
      </svg>
    );
  }

  return (
    <svg width={size} height={size} viewBox="22 27 461 461" fill="none">
      <path fill={disc} d={DISC} />
      <g fill={mark}>{MARKS}</g>
    </svg>
  );
}

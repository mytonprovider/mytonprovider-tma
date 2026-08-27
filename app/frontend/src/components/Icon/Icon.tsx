import { type Glyph, GLYPHS, type GlyphName } from "./glyphs";

interface IconProps {
  glyph: GlyphName;
  size?: number;
  stroke?: number;
  filled?: boolean;
  color?: string;
  fill?: string;
  strokeColor?: string;
}

export function Icon({
  glyph,
  size = 22,
  stroke,
  filled = false,
  color = "currentColor",
  fill,
  strokeColor,
}: IconProps) {
  const g: Glyph = GLYPHS[glyph];
  const isFill = g.fill === "fill";

  let fillValue: string;
  let strokeValue: string;
  let strokeWidth: number | undefined;
  if (isFill) {
    fillValue = fill ?? color;
    strokeValue = "none";
  } else {
    strokeValue = strokeColor ?? color;
    strokeWidth = stroke ?? g.s;
    fillValue = fill ?? (filled ? color : "none");
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox={g.vb ?? "0 0 24 24"}
      fill={fillValue}
      stroke={strokeValue}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: "block", flex: "none" }}
      dangerouslySetInnerHTML={{ __html: g.inner }}
    />
  );
}

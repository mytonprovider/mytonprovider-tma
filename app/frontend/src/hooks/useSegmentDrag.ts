import { type PointerEvent as ReactPointerEvent, type RefObject, useRef, useState } from "react";

const SLOP = 4;

interface Held {
  pointerId: number;
  startX: number;
  grab: number;
  index: number;
  active: boolean;
}

interface SegmentDrag {
  offset: number | null;
  handlers: {
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onLostPointerCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  };
}

export function useSegmentDrag(
  boxRef: RefObject<HTMLDivElement>,
  count: number,
  activeIndex: number,
  onIndex: (index: number) => void,
  onScrub?: (position: number | null) => void,
): SegmentDrag {
  const held = useRef<Held | null>(null);
  const [offset, setOffset] = useState<number | null>(null);

  const metrics = () => {
    const box = boxRef.current;
    if (!box) return null;
    const rect = box.getBoundingClientRect();
    const padding = parseFloat(getComputedStyle(box).paddingLeft) || 0;
    const span = (rect.width - padding * 2) / count;
    return { left: rect.left + padding, span, limit: (count - 1) * span };
  };

  const apply = (clientX: number) => {
    const size = metrics();
    const drag = held.current;
    if (!size || !drag) return;
    const position = Math.max(0, Math.min(size.limit, clientX - size.left - drag.grab));
    setOffset(position);
    onScrub?.(position / size.span);
    const index = Math.max(0, Math.min(count - 1, Math.round(position / size.span)));
    if (index === drag.index) return;
    drag.index = index;
    onIndex(index);
  };

  const stop = (pointerId?: number) => {
    const drag = held.current;
    if (!drag || (pointerId !== undefined && pointerId !== drag.pointerId)) return;
    held.current = null;
    if (!drag.active) return;
    setOffset(null);
    onScrub?.(null);
  };

  return {
    offset,
    handlers: {
      onPointerDown: (event) => {
        if (event.button !== 0 || !event.isPrimary) return;
        const size = metrics();
        if (!size) return;
        const inside = event.clientX - size.left - activeIndex * size.span;
        held.current = {
          pointerId: event.pointerId,
          startX: event.clientX,
          grab: inside >= 0 && inside <= size.span ? inside : size.span / 2,
          index: activeIndex,
          active: false,
        };
      },
      onPointerMove: (event) => {
        const drag = held.current;
        if (!drag || event.pointerId !== drag.pointerId) return;
        if (!drag.active) {
          if (Math.abs(event.clientX - drag.startX) < SLOP) return;
          drag.active = true;
          boxRef.current?.setPointerCapture(event.pointerId);
        }
        apply(event.clientX);
      },
      onPointerUp: (event) => stop(event.pointerId),
      onPointerCancel: (event) => stop(event.pointerId),
      onLostPointerCapture: (event) => {
        if (event.target === boxRef.current) stop(event.pointerId);
      },
    },
  };
}

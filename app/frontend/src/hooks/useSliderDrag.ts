import { type PointerEvent as ReactPointerEvent, type RefObject } from "react";

export function useSliderDrag(
  trackRef: RefObject<HTMLDivElement>,
  onRatio: (ratio: number) => void,
): (event: ReactPointerEvent) => void {
  return (event) => {
    event.preventDefault();
    const move = (moveEvent: PointerEvent) => {
      const track = trackRef.current;
      if (!track) return;
      const rect = track.getBoundingClientRect();
      onRatio(Math.max(0, Math.min(1, (moveEvent.clientX - rect.left) / rect.width)));
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
    window.addEventListener("pointercancel", stop);
  };
}

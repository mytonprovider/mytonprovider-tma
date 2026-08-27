import {
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
  type RefCallback,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

const SLOP = 6;
const CLOSE_RATIO = 0.25;
const CLOSE_VELOCITY = 0.4;

interface SheetDrag {
  ref: RefCallback<HTMLDivElement>;
  element: MutableRefObject<HTMLDivElement | null>;
  offset: number;
  dragging: boolean;
  handlers: {
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  };
}

interface DragState {
  startX: number;
  startY: number;
  startTime: number;
  height: number;
  scroller: Element | null;
  decided: boolean;
  active: boolean;
}

const IDLE: DragState = {
  startX: 0,
  startY: 0,
  startTime: 0,
  height: 0,
  scroller: null,
  decided: true,
  active: false,
};

function scrollerAt(target: Element, sheet: Element): Element | null {
  let node: Element | null = target;
  while (node && sheet.contains(node)) {
    if (node.scrollHeight > node.clientHeight) {
      const overflow = getComputedStyle(node).overflowY;
      if (overflow === "auto" || overflow === "scroll") return node;
    }
    node = node.parentElement;
  }
  return null;
}

export function useSheetDrag(enabled: boolean, onDismiss: () => void): SheetDrag {
  const [offset, setOffset] = useState(0);
  const [dragging, setDragging] = useState(false);
  const sheet = useRef<HTMLDivElement | null>(null);
  const state = useRef<DragState>(IDLE);
  const frame = useRef(0);
  const live = useRef({ enabled, onDismiss });
  live.current = { enabled, onDismiss };

  const begin = useCallback((target: Element, x: number, y: number) => {
    const element = sheet.current;
    if (!live.current.enabled || !element || target.closest("[data-no-drag]")) {
      state.current = IDLE;
      return;
    }
    state.current = {
      startX: x,
      startY: y,
      startTime: performance.now(),
      height: element.getBoundingClientRect().height,
      scroller: scrollerAt(target, element),
      decided: false,
      active: false,
    };
  }, []);

  const move = useCallback((x: number, y: number): boolean => {
    const drag = state.current;
    if (drag.decided && !drag.active) return false;
    const dy = y - drag.startY;

    if (!drag.decided) {
      const dx = x - drag.startX;
      if (Math.abs(dy) < SLOP && Math.abs(dx) < SLOP) return false;
      drag.decided = true;
      const atTop = !drag.scroller || drag.scroller.scrollTop <= 0;
      drag.active = dy > Math.abs(dx) && atTop;
      if (!drag.active) return false;
      setDragging(true);
    }

    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setOffset(Math.max(0, dy)));
    return true;
  }, []);

  const finish = useCallback((y: number) => {
    const drag = state.current;
    state.current = IDLE;
    if (!drag.active) return;
    cancelAnimationFrame(frame.current);
    setDragging(false);
    const distance = y - drag.startY;
    const elapsed = performance.now() - drag.startTime;
    const velocity = elapsed > 0 ? distance / elapsed : 0;
    if (distance <= drag.height * CLOSE_RATIO && velocity <= CLOSE_VELOCITY) {
      setOffset(0);
      return;
    }
    live.current.onDismiss();
  }, []);

  const onTouchStart = useCallback(
    (event: TouchEvent) => {
      const touch = event.touches[0];
      if (event.touches.length !== 1 || !touch) return;
      begin(event.target as Element, touch.clientX, touch.clientY);
    },
    [begin],
  );

  const onTouchMove = useCallback(
    (event: TouchEvent) => {
      const touch = event.touches[0];
      if (!touch) return;
      if (move(touch.clientX, touch.clientY) && event.cancelable) event.preventDefault();
    },
    [move],
  );

  const onTouchEnd = useCallback(
    (event: TouchEvent) => {
      const touch = event.changedTouches[0];
      finish(touch ? touch.clientY : state.current.startY);
    },
    [finish],
  );

  const ref = useCallback<RefCallback<HTMLDivElement>>(
    (element) => {
      const previous = sheet.current;
      if (previous) {
        previous.removeEventListener("touchstart", onTouchStart);
        previous.removeEventListener("touchmove", onTouchMove);
        previous.removeEventListener("touchend", onTouchEnd);
        previous.removeEventListener("touchcancel", onTouchEnd);
      }
      sheet.current = element;
      if (!element) return;
      element.addEventListener("touchstart", onTouchStart, { passive: true });
      element.addEventListener("touchmove", onTouchMove, { passive: false });
      element.addEventListener("touchend", onTouchEnd);
      element.addEventListener("touchcancel", onTouchEnd);
    },
    [onTouchStart, onTouchMove, onTouchEnd],
  );

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  return {
    ref,
    element: sheet,
    offset,
    dragging,
    handlers: {
      onPointerDown: (event) => {
        if (event.pointerType !== "mouse") return;
        begin(event.target as Element, event.clientX, event.clientY);
      },
      onPointerMove: (event) => {
        if (event.pointerType !== "mouse") return;
        move(event.clientX, event.clientY);
      },
      onPointerUp: (event) => {
        if (event.pointerType !== "mouse") return;
        finish(event.clientY);
      },
      onPointerCancel: (event) => {
        if (event.pointerType !== "mouse") return;
        finish(event.clientY);
      },
    },
  };
}

import { useLayerHost } from "@/app/layers/context";
import { Sheet } from "@/app/layers/Sheet";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface BottomSheetProps {
  title?: string;
  subtitle?: ReactNode;
  onClose: () => void;
  children: (close: () => void) => ReactNode;
}

export function BottomSheet({ title, subtitle, onClose, children }: BottomSheetProps) {
  const host = useLayerHost();
  const [closing, setClosing] = useState(false);
  const slot = useRef(0);
  const close = useRef(() => setClosing(true));

  useEffect(() => {
    if (!host) return;
    slot.current = host.open(() => close.current());
    const id = slot.current;
    return () => host.drop(id);
  }, []);

  const index = host ? host.dialogs.findIndex((entry) => entry.id === slot.current) : -1;
  const depth = (host?.routeDepth ?? 0) + Math.max(index, 0) + 1;
  const top = !host || index === host.dialogs.length - 1;

  const sheet = (
    <Sheet
      height="auto"
      depth={depth}
      top={top}
      closing={closing}
      title={title}
      subtitle={subtitle}
      onDismiss={() => close.current()}
      onClosed={onClose}
    >
      {children(() => close.current())}
    </Sheet>
  );

  return host?.container ? createPortal(sheet, host.container) : sheet;
}

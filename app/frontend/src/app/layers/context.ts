import { createContext, useContext } from "react";

export interface DialogSlot {
  id: number;
  close: () => void;
}

export interface LayerHost {
  container: HTMLElement | null;
  routeDepth: number;
  dialogs: DialogSlot[];
  open: (close: () => void) => number;
  drop: (id: number) => void;
}

export const LayerContext = createContext<LayerHost | null>(null);

let dialogsOpen = false;

export function setDialogsOpen(open: boolean): void {
  dialogsOpen = open;
}

export function hasDialogs(): boolean {
  return dialogsOpen;
}

export function useLayerHost(): LayerHost | null {
  return useContext(LayerContext);
}

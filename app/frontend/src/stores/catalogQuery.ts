import type { CatalogFilters, Sort, SortField } from "@/data/types";
import { create } from "zustand";

export type Tab = "list" | "subs" | "fav";

const EMPTY_FILTERS: CatalogFilters = {
  location: null,
  rating: null,
  uptime: null,
  price: null,
  bag: null,
  cores: null,
  ram: null,
  age: null,
  minSpan: null,
  maxSpan: null,
  space: null,
  diskRead: null,
  diskWrite: null,
  download: null,
  upload: null,
  ping: null,
  cpuVirtual: null,
  storageHash: null,
  providerHash: null,
  freeSpace: false,
  telemetry: null,
  stableOnly: false,
};

export const PAGE_SIZE = 10;

const START_TAB_KEY = "mtp-start-tab";

function startTab(): Tab {
  try {
    const saved = localStorage.getItem(START_TAB_KEY);
    return saved === "subs" || saved === "fav" ? saved : "list";
  } catch {
    return "list";
  }
}

export function rememberStartTab(tab: Tab): void {
  try {
    localStorage.setItem(START_TAB_KEY, tab);
  } catch {
    return;
  }
}

type Visible = Record<Tab, number>;

const FIRST_PAGE: Visible = { list: PAGE_SIZE, subs: PAGE_SIZE, fav: PAGE_SIZE };

const SHAPE_KEY = "mtp-list-shape";
const TABS: Tab[] = ["list", "subs", "fav"];

interface ListShape {
  shown: number;
  total: number;
}

const COLD_SHAPE: Record<Tab, ListShape> = {
  list: { shown: PAGE_SIZE, total: 0 },
  subs: { shown: PAGE_SIZE, total: 0 },
  fav: { shown: PAGE_SIZE, total: 0 },
};

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

// How long each tab was when the app was last closed: the list comes back the same size
// and the skeleton draws that many rows instead of a guess.
function storedShapes(): Record<Tab, ListShape> {
  const shapes = { ...COLD_SHAPE };
  try {
    const saved = JSON.parse(localStorage.getItem(SHAPE_KEY) ?? "{}") as Record<string, unknown>;
    for (const tab of TABS) {
      const { shown, total } = (saved[tab] ?? {}) as { shown?: unknown; total?: unknown };
      if (isCount(shown) && shown > 0 && isCount(total) && total >= shown) shapes[tab] = { shown, total };
    }
  } catch {
    return shapes;
  }
  return shapes;
}

export const listShapes = storedShapes();

export function rememberShape(tab: Tab, shown: number, total: number): void {
  const current = listShapes[tab];
  if (current.shown === shown && current.total === total) return;
  listShapes[tab] = { shown, total };
  try {
    localStorage.setItem(SHAPE_KEY, JSON.stringify(listShapes));
  } catch {
    return;
  }
}

interface CatalogQueryState {
  tab: Tab;
  search: string;
  sort: Sort;
  filters: CatalogFilters;
  visible: Visible;
  setTab: (tab: Tab) => void;
  setSearch: (search: string) => void;
  setSortField: (field: SortField) => void;
  setFilters: (filters: CatalogFilters) => void;
  resetFilters: () => void;
  loadMore: (tab: Tab) => void;
}

export const useCatalogQuery = create<CatalogQueryState>((set) => ({
  tab: startTab(),
  search: "",
  sort: { field: "rating", dir: "desc" },
  filters: EMPTY_FILTERS,
  visible: { list: listShapes.list.shown, subs: listShapes.subs.shown, fav: listShapes.fav.shown },
  setTab: (tab) => set({ tab }),
  setSearch: (search) => set({ search, visible: FIRST_PAGE }),
  setSortField: (field) =>
    set((state) => ({
      sort:
        state.sort.field === field
          ? { field, dir: state.sort.dir === "asc" ? "desc" : "asc" }
          : { field, dir: "desc" },
    })),
  setFilters: (filters) => set({ filters, visible: FIRST_PAGE }),
  resetFilters: () => set({ filters: EMPTY_FILTERS, visible: FIRST_PAGE }),
  loadMore: (tab) => set((state) => ({ visible: { ...state.visible, [tab]: state.visible[tab] + PAGE_SIZE } })),
}));

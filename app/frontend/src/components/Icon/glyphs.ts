export interface Glyph {
  s?: number;
  fill?: "fill";
  vb?: string;
  inner: string;
}

export const GLYPHS = {
  menu: { s: 1.8, inner: '<path d="M4 7h16M4 12h16M4 17h16"/>' },
  reload: { s: 1.7, inner: '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>' },
  search: { s: 2, inner: '<circle cx="11" cy="11" r="7"/><line x1="16.65" y1="16.65" x2="21" y2="21"/>' },
  warn: {
    s: 1.8,
    inner:
      '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  },
  close: { s: 3, inner: '<path d="M6 6l12 12M18 6L6 18"/>' },
  bell: {
    s: 1.7,
    inner:
      '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  },
  bellOff: {
    s: 1.7,
    inner:
      '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/><line x1="3" y1="3" x2="21" y2="21"/>',
  },
  sliders: {
    s: 1.8,
    vb: "0 0 22 22",
    inner:
      '<line x1="3" y1="7" x2="13" y2="7"/><line x1="3" y1="15" x2="9" y2="15"/><circle cx="16" cy="7" r="2.4"/><circle cx="12" cy="15" r="2.4"/><line x1="18" y1="7" x2="19" y2="7"/><line x1="14" y1="15" x2="19" y2="15"/>',
  },
  chevronDown: { s: 2.6, inner: '<path d="M6 9l6 6 6-6"/>' },
  arrowUpRight: { s: 2.2, inner: '<path d="M7 17L17 7M9 7h8v8"/>' },
  arrowUp: { s: 2.4, inner: '<path d="M12 19V5M5 12l7-7 7 7"/>' },
  arrowLeft: { s: 2.1, inner: '<line x1="20" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>' },
  star: {
    s: 1.7,
    inner:
      '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  },
  grid: {
    s: 1.7,
    inner:
      '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
  },
  clock: { s: 2, inner: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>' },
  cpu: {
    s: 2,
    inner:
      '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/>',
  },
  bars: {
    s: 2,
    inner:
      '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  },
  globe: {
    s: 2,
    inner:
      '<circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>',
  },
  server: {
    s: 2,
    inner:
      '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><line x1="7" y1="7.5" x2="7.01" y2="7.5"/><line x1="7" y1="16.5" x2="7.01" y2="16.5"/>',
  },
  calendar: {
    s: 2,
    inner:
      '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  },
  history: { s: 2, inner: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>' },
  logout: {
    s: 2.1,
    inner:
      '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  },
  info: {
    s: 2,
    inner:
      '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  },
  lock: { s: 2, inner: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>' },
  eye: { s: 2, inner: '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>' },
  check: { s: 2.6, inner: '<path d="M5 13l4 4L19 7"/>' },
  chevron: { s: 2.2, inner: '<path d="M9 6l6 6-6 6"/>' },
  external: { s: 2, inner: '<path d="M8 16 16 8"/><path d="M9 8h7v7"/>' },
  edit: {
    s: 2,
    inner:
      '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
      + '<path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
  },
  copy: {
    s: 2,
    inner: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  },
  telegram: {
    fill: "fill",
    inner:
      '<path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/>',
  },
} satisfies Record<string, Glyph>;

export type GlyphName = keyof typeof GLYPHS;

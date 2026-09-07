import { formatBytes, formatMbits, formatPrice, formatSpace } from "@/lib/format";
import { describe, expect, it } from "vitest";
import { baseDto, overfilled, providerWith, providers, silent, stable } from "./fixtures";
import { computeBounds, computeRanks, countActiveFilters, selectCatalog } from "./query";
import type { CatalogFilters, Provider, Range, RangeKey } from "./types";

const NO_FILTERS: CatalogFilters = {
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
  location: null,
  cpuVirtual: null,
  storageHash: null,
  providerHash: null,
  freeSpace: false,
  telemetry: null,
  stableOnly: false,
};

type Selection = Parameters<typeof selectCatalog>[1];

function select(list: Provider[], over: Partial<Selection> = {}): Provider[] {
  return selectCatalog(list, {
    only: null,
    search: "",
    filters: NO_FILTERS,
    sort: { field: "rating", dir: "desc" },
    names: {},
    bounds: null,
    ...over,
  });
}

function pick(list: Provider[], filters: Partial<CatalogFilters>, search = ""): Provider[] {
  return select(list, { filters: { ...NO_FILTERS, ...filters }, search });
}

function keeps(key: RangeKey, range: Range): boolean {
  return pick([stable], { [key]: range }).length === 1;
}

// Filter and card are wired separately; a mismatch shows up only as a provider
// missing from its own range.
describe("filter scale", () => {
  it("matches the card on RAM, which arrives in decimal gigabytes", () => {
    expect(formatSpace(stable.telemetry.totalRamBytes)).toBe("3.73 GB");
    expect(keeps("ram", [3.7, 3.8])).toBe(true);
    expect(keeps("ram", [4, 8])).toBe(false);
  });

  it("matches the card on disk, which arrives in GiB", () => {
    expect(formatSpace(stable.telemetry.totalSpaceBytes)).toBe("3820 GB");
    expect(keeps("space", [3820, 3820])).toBe(true);
  });

  it("matches the card on network speed, which arrives in bits", () => {
    expect(formatMbits(stable.telemetry.downloadSpeed)).toBe("1970 Mbit/s");
    expect(keeps("download", [1970, 1971])).toBe(true);
    expect(keeps("upload", [1177, 1178])).toBe(true);
  });

  it("matches the card on bag size and price", () => {
    expect(formatBytes(stable.maxBagBytes)).toBe("80 GB");
    expect(keeps("bag", [80, 80])).toBe(true);
    expect(formatPrice(stable.price)).toBe("10");
    expect(keeps("price", [10, 10.01])).toBe(true);
  });

  it("matches the card on disk speed, which fio reports on its own scale", () => {
    expect(keeps("diskRead", [63, 64])).toBe(true);
    expect(keeps("diskWrite", [18, 19])).toBe(true);
  });

  it("counts spans in days, and age from registration to right now", () => {
    expect(keeps("minSpan", [7, 7])).toBe(true);
    expect(keeps("maxSpan", [76, 77])).toBe(true);

    const tenDaysOld = providerWith({ reg_time: Math.floor(Date.now() / 1000) - 10 * 86400 });

    expect(pick([tenDaysOld], { age: [9.9, 10.1] }).length).toBe(1);
    expect(pick([tenDaysOld], { age: [11, 20] }).length).toBe(0);
  });
});

describe("selectCatalog", () => {
  it("drops a provider whose value nobody knows", () => {
    expect(pick(providers, {}).length).toBe(providers.length);
    expect(pick(providers, { ram: [0, 1000] })).not.toContain(silent);
    expect(pick(providers, { ping: [0, 1000] })).not.toContain(silent);
  });

  it("treats a ping at the ceiling as no answer", () => {
    const deaf = providerWith({ telemetry: { ...baseDto.telemetry, speedtest_ping: 10000 } });

    expect(pick([deaf], { ping: [0, 10000] }).length).toBe(0);
  });

  it("narrows by the flags", () => {
    expect(pick(providers, { telemetry: true })).not.toContain(silent);
    expect(pick(providers, { telemetry: false })).toEqual([silent]);
    expect(pick(providers, { stableOnly: true })).not.toContain(silent);
    expect(pick(providers, { freeSpace: true })).toEqual([stable]);
    expect(pick(providers, { location: "RU" }).length).toBe(3);
    expect(pick(providers, { location: "JP" }).length).toBe(0);
  });

  it("searches the key and the name the owner gave", () => {
    expect(pick(providers, {}, stable.pubkey.slice(-6))).toEqual([stable]);
    expect(select(providers, { search: "moscow", names: { [silent.pubkey]: "Moscow node" } })).toEqual([silent]);
  });

  it("restricts the tab to its own keys", () => {
    expect(select(providers, { only: [silent.pubkey] })).toEqual([silent]);
  });

  it("sorts by the field it is given", () => {
    expect(pick(providers, {}).map((p) => p.rating)).toEqual([20.415426, 16.33, 0]);
    const asc = select(providers, { sort: { field: "rating", dir: "asc" } });

    expect(asc.map((p) => p.rating)).toEqual([0, 16.33, 20.415426]);
  });
});

describe("computeBounds", () => {
  it("cuts the scale at p95 and keeps the outliers reachable", () => {
    const many = Array.from({ length: 20 }, (_, i) => providerWith({ rating: i }, String(i).padStart(6, "0")));
    const giant = providerWith({ rating: 500 }, "999999");
    const bounds = computeBounds([...many, giant]);

    expect(bounds.rating).toEqual([0, 19]);
    expect(select([giant], { filters: { ...NO_FILTERS, rating: bounds.rating }, bounds })).toEqual([giant]);
  });

  it("keeps uptime on its own full scale", () => {
    expect(computeBounds(providers).uptime).toEqual([0, 100]);
  });

  it("falls back when nothing is measured", () => {
    expect(computeBounds([]).rating).toEqual([0, 1]);
    expect(computeBounds([silent]).ram).toEqual([0, 1]);
  });
});

describe("computeRanks", () => {
  it("ranks by rating and leaves the unrated out", () => {
    const ranks = computeRanks(providers);

    expect(ranks[stable.pubkey]).toBe(1);
    expect(ranks[overfilled.pubkey]).toBe(2);
    expect(ranks[silent.pubkey]).toBe(undefined);
  });
});

describe("countActiveFilters", () => {
  it("counts every dimension once", () => {
    expect(countActiveFilters(NO_FILTERS)).toBe(0);
    expect(countActiveFilters({ ...NO_FILTERS, ram: [0, 8], location: "RU", stableOnly: true })).toBe(3);
    expect(countActiveFilters({ ...NO_FILTERS, telemetry: false, cpuVirtual: false })).toBe(2);
  });
});

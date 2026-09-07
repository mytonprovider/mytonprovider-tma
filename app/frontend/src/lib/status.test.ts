import type { BagState } from "@/data/backend";
import { providerWith, silent, stable } from "@/data/fixtures";
import { en } from "@/i18n/en";
import { ru } from "@/i18n/ru";
import { describe, expect, it } from "vitest";
import { ACCENT, SC, type StatusTone } from "./colors";
import { describeStatus, filterColor, reasonText, reasonTone, stateText, stateTone, statusTone } from "./status";

// Typed by BagState: a state added on the backend stops the build here.
const STATE_TONES: Record<BagState, StatusTone> = {
  confirmed: "green",
  downloading: "yellow",
  not_accepted: "gray",
  unavailable: "orange",
  not_confirmed: "red",
  not_paid: "orange",
  closed: "gray",
  partial: "yellow",
  not_hired: "gray",
};

describe("bag states", () => {
  it("gives every state a tone and a name in both locales", () => {
    for (const [state, tone] of Object.entries(STATE_TONES) as [BagState, StatusTone][]) {
      expect(stateTone(state)).toBe(tone);
      expect(stateText(state, en)).toBeTruthy();
      expect(stateText(state, ru)).toBeTruthy();
    }
  });

  it("colours the slices that are not states apart", () => {
    expect(filterColor("all")).toBe(ACCENT);
    expect(filterColor("check")).toBe(SC.gray);
    expect(filterColor("confirmed")).toBe(SC.green);
  });
});

describe("reasonTone", () => {
  it("weighs the check codes by what they mean", () => {
    expect(reasonTone(301)).toBe("red");
    expect(reasonTone(401)).toBe("orange");
    expect(reasonTone(103)).toBe("yellow");
    expect(reasonTone(0)).toBe("gray");
    expect(reasonTone(999)).toBe("gray");
  });
});

describe("reasonText", () => {
  it("reads the code upstream sent, and says so when it does not know it", () => {
    expect(reasonText(401, en)).toBe(en.reason[401]);
    expect(reasonText(null, en)).toBe(en.reason.none);
    expect(reasonText(999, en)).toBe(en.unknownReason(999));
  });
});

describe("describeStatus", () => {
  it("reads the ratio upstream sent", () => {
    const view = describeStatus(stable, en);

    expect(view.tone).toBe("green");
    expect(view.label).toBe(en.status.stable);
    expect(view.desc).toBe(en.bagsFailed);
    expect(view.hasRatio).toBe(true);
    expect(view.ratio).toBeCloseTo(0.9977, 4);
    expect(view.passed).toBe(432);
    expect(view.total).toBe(433);
    expect(view.problems).toBe(1);
  });

  it("counts the checks itself when the ratio is missing", () => {
    const partial = providerWith({
      status_ratio: null,
      statuses_reason_stats: [
        { reason: 0, cnt: 8 },
        { reason: 401, cnt: 2 },
      ],
    });
    const unstable = providerWith({
      status_ratio: null,
      statuses_reason_stats: [
        { reason: 0, cnt: 7 },
        { reason: 401, cnt: 3 },
      ],
    });

    expect(describeStatus(partial, en).ratio).toBeCloseTo(0.8, 4);
    expect(describeStatus(partial, en).label).toBe(en.status.partial);
    expect(describeStatus(unstable, en).label).toBe(en.status.unstable);
  });

  it("names the last check when nothing failed", () => {
    const clean = providerWith({ statuses_reason_stats: [{ reason: 0, cnt: 432 }] });
    const view = describeStatus(clean, en);

    expect(view.problems).toBe(0);
    expect(view.desc).toBe(en.reason[0]);
  });

  it("groups a failing status the same way as a check code", () => {
    expect(describeStatus(providerWith({ status: 203 }), en).label).toBe(en.status.unavailable);
    expect(describeStatus(providerWith({ status: 301 }), en).label).toBe(en.status.notStored);
    expect(describeStatus(providerWith({ status: 401 }), en).label).toBe(en.status.noProofs);
    expect(describeStatus(providerWith({ status: 999 }), en).label).toBe(en.status.unknown);
  });

  it("keeps a provider that was never checked out of the scale", () => {
    const view = describeStatus(silent, en);

    expect(statusTone(silent)).toBe("gray");
    expect(view.label).toBe(en.status.noData);
    expect(view.desc).toBe(en.reason.none);
    expect(view.hasRatio).toBe(false);
    expect(view.total).toBe(0);
  });
});

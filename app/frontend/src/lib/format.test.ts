import { en } from "@/i18n/en";
import { describe, expect, it } from "vitest";
import {
  BYTES_IN_GIB,
  ago,
  diskSpeedToNum,
  fitKey,
  formatBytes,
  formatDiskSpeed,
  formatMbits,
  formatPing,
  formatSpace,
  formatSpacePair,
  formatTime,
  freeSpaceTone,
  levelTone,
  shorten,
  spaceFreePercent,
  trim,
  trimDown,
  uptimeTone,
} from "./format";

describe("formatBytes", () => {
  it("steps by 1024 and labels the steps in Latin", () => {
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1024 ** 2)).toBe("1 MB");
    expect(formatBytes(4.28e9)).toBe("3.99 GB");
    expect(formatBytes(1024 ** 4)).toBe("1 TB");
  });

  it("stops at TB and drops the fraction from four digits up", () => {
    expect(formatBytes(1024 ** 5)).toBe("1024 TB");
    expect(formatBytes(14000 * BYTES_IN_GIB)).toBe("13.67 TB");
  });

  it("has nothing to show for zero, negatives and missing values", () => {
    expect(formatBytes(0)).toBe("—");
    expect(formatBytes(-1)).toBe("—");
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(Number.NaN)).toBe("—");
  });
});

describe("formatSpace", () => {
  it("keeps disk and RAM in gigabytes, the way the installer asks for them", () => {
    expect(formatSpace(14000 * BYTES_IN_GIB)).toBe("14000 GB");
    expect(formatSpace(3689 * BYTES_IN_GIB)).toBe("3689 GB");
    expect(formatSpace(4.01e9)).toBe("3.73 GB");
  });

  it("rounds from a thousand up", () => {
    expect(formatSpace(999.5 * BYTES_IN_GIB)).toBe("999.5 GB");
    expect(formatSpace(1000 * BYTES_IN_GIB)).toBe("1000 GB");
  });
});

describe("formatSpacePair", () => {
  it("writes the unit once and both halves on the same scale", () => {
    expect(formatSpacePair(3656.41 * BYTES_IN_GIB, 3820 * BYTES_IN_GIB)).toBe("3656 / 3820 GB");
    expect(formatSpacePair(1.5 * BYTES_IN_GIB, 100 * BYTES_IN_GIB)).toBe("1.5 / 100 GB");
  });

  it("shows nothing when either half is unknown or the disk is empty", () => {
    expect(formatSpacePair(null, 100 * BYTES_IN_GIB)).toBe("—");
    expect(formatSpacePair(1, 0)).toBe("—");
  });
});

describe("trim", () => {
  it("rounds, unlike trimDown which cuts", () => {
    expect(trim(0.999, 2)).toBe("1");
    expect(trimDown(0.999, 2)).toBe("0.99");
    expect(trim(20.415426, 2)).toBe("20.42");
    expect(trimDown(20.415426, 2)).toBe("20.41");
  });
});

describe("formatTime", () => {
  it("counts seconds below a minute", () => {
    expect(formatTime(45, en)).toBe("45 sec");
  });

  it("switches unit at each boundary", () => {
    expect(formatTime(3599, en)).toBe("59 min 59 sec");
    expect(formatTime(3600, en)).toBe("1 hr");
    expect(formatTime(86400, en)).toBe("1 days");
    expect(formatTime(27064916, en)).toBe("313 days 6 hr");
    expect(formatTime(63504000, en)).toBe("2 year 5 days");
  });

  it("drops the smaller unit when asked", () => {
    expect(formatTime(3599, en, true)).toBe("59 min");
    expect(formatTime(27064916, en, true)).toBe("313 days");
  });
});

describe("ago", () => {
  it("calls the last minute just now", () => {
    expect(ago(59, en)).toBe("Just now");
    expect(ago(120, en)).toBe("2 min ago");
  });
});

describe("formatMbits", () => {
  it("reads the speedtest as bits and prints megabits", () => {
    expect(formatMbits(1970199300)).toBe("1970 Mbit/s");
    expect(formatMbits(0)).toBe("—");
    expect(formatMbits(null)).toBe("—");
  });
});

describe("formatPing", () => {
  it("rounds to milliseconds and treats the ceiling as no answer", () => {
    expect(formatPing(15.970891)).toBe("16 ms");
    expect(formatPing(10000)).toBe("—");
    expect(formatPing(0)).toBe("—");
  });
});

describe("formatDiskSpeed", () => {
  it("keeps fio numbers on their own 1024 scale", () => {
    expect(diskSpeedToNum("63.9MiB/s")).toBeCloseTo(63.9 * 1048576, 0);
    expect(diskSpeedToNum("1.2GiB/s")).toBeCloseTo(1.2 * 1073741824, 0);
    expect(formatDiskSpeed("63.9MiB/s")).toBe("63.9 MiB/s");
    expect(formatDiskSpeed("1.2GiB/s")).toBe("1228.8 MiB/s");
  });

  it("gives up on anything it cannot parse", () => {
    expect(diskSpeedToNum(null)).toBe(null);
    expect(diskSpeedToNum("n/a")).toBe(null);
    expect(formatDiskSpeed("n/a")).toBe("—");
  });
});

describe("shorten", () => {
  it("keeps the head and the tail of a key", () => {
    expect(shorten("3a65231e59031a3a0c6f363030712730", 16)).toBe("3a65231e…30712730");
    expect(shorten("short", 16)).toBe("short");
  });

});

describe("fitKey", () => {
  it("fits a key into the width it is given", () => {
    expect(fitKey("3a65231e59031a3a0c6f363030712730", 13)).toBe("3a6523…712730");
    expect(fitKey("3a65231e5903", 13)).toBe("3a65231e5903");
  });
});

describe("spaceFreePercent", () => {
  it("measures what is left and stays inside the scale", () => {
    expect(spaceFreePercent(3820 * BYTES_IN_GIB, 3656.41 * BYTES_IN_GIB)).toBeCloseTo(4.28, 2);
    expect(spaceFreePercent(100, 120)).toBe(0);
    expect(spaceFreePercent(0, 0)).toBe(null);
    expect(spaceFreePercent(null, 10)).toBe(null);
  });
});

describe("tones", () => {
  it("turns free space red before the disk is full", () => {
    expect(freeSpaceTone(15)).toBe("red");
    expect(freeSpaceTone(25)).toBe("orange");
    expect(freeSpaceTone(26)).toBe("green");
  });

  it("warns a level before it reaches the threshold", () => {
    expect(levelTone(80, 80)).toBe("red");
    expect(levelTone(68, 80)).toBe("orange");
    expect(levelTone(67, 80)).toBe("green");
  });

  it("greys out uptime nobody measured", () => {
    expect(uptimeTone(99)).toBe("green");
    expect(uptimeTone(95)).toBe("yellow");
    expect(uptimeTone(94)).toBe("red");
    expect(uptimeTone(0)).toBe("gray");
  });
});

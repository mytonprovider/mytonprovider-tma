import { BYTES_IN_GB, BYTES_IN_GIB } from "@/lib/format";
import { describe, expect, it } from "vitest";
import { adaptProvider } from "./adapt";
import type { ProviderDto, TelemetryDto } from "./dto";
import { NOW, baseDto, stable } from "./fixtures";

describe("adaptProvider", () => {
  // Upstream mixes the units on purpose and this is the only place they are converted.
  it("reads disk in GiB and RAM in decimal gigabytes", () => {
    expect(stable.telemetry.totalSpaceBytes).toBe(3820 * BYTES_IN_GIB);
    expect(stable.telemetry.usedSpaceBytes).toBeCloseTo(3656.41 * BYTES_IN_GIB, 0);
    expect(stable.telemetry.totalRamBytes).toBe(4.01 * BYTES_IN_GB);
    expect(stable.telemetry.usageRamBytes).toBeCloseTo(1.14 * BYTES_IN_GB, 0);
  });

  it("leaves the values that already arrive in their own unit alone", () => {
    expect(stable.maxBagBytes).toBe(baseDto.max_bag_size_bytes);
    expect(stable.telemetry.downloadSpeed).toBe(baseDto.telemetry.speedtest_download);
    expect(stable.telemetry.ping).toBe(baseDto.telemetry.speedtest_ping);
    expect(stable.price).toBe(baseDto.price);
  });

  it("renames the check counters", () => {
    expect(stable.statusReasons).toEqual([
      { reason: 0, count: 432 },
      { reason: 401, count: 1 },
    ]);
  });

  it("measures staleness against the moment the catalog was read", () => {
    expect(stable.staleSec).toBe(93);
    expect(stable.telemetryStaleSec).toBe(138);
  });

  it("never reports a negative age when the clocks disagree", () => {
    const ahead = adaptProvider({ ...baseDto, last_online_check_time: NOW + 30 }, NOW);

    expect(ahead.staleSec).toBe(0);
  });

  it("counts a provider that was never checked as fresh, not as ancient", () => {
    const never = adaptProvider({ ...baseDto, last_online_check_time: null, telemetry: {} }, NOW);

    expect(never.staleSec).toBe(0);
    expect(never.telemetryStaleSec).toBe(0);
  });

  // The schema is unstable: fields go missing and the whole blob comes as null.
  it("survives a telemetry blob that is empty or missing", () => {
    const empty = adaptProvider({ ...baseDto, telemetry: {} }, NOW);
    const missing = adaptProvider(
      { ...baseDto, telemetry: null as unknown as TelemetryDto, statuses_reason_stats: undefined },
      NOW,
    );

    expect(empty.telemetry.totalSpaceBytes).toBe(null);
    expect(empty.telemetry.cpuCount).toBe(null);
    expect(missing.telemetry.totalRamBytes).toBe(null);
    expect(missing.statusReasons).toEqual([]);
  });

  it("drops a value that is not a finite number", () => {
    const broken: ProviderDto = {
      ...baseDto,
      telemetry: { ...baseDto.telemetry, total_ram: Number.NaN, total_provider_space: null },
    };
    const adapted = adaptProvider(broken, NOW);

    expect(adapted.telemetry.totalRamBytes).toBe(null);
    expect(adapted.telemetry.totalSpaceBytes).toBe(null);
  });

  it("keeps the location it was given and nothing when there is none", () => {
    expect(stable.location?.countryIso).toBe("RU");
    expect(adaptProvider({ ...baseDto, location: null }, NOW).location).toBe(null);
  });
});

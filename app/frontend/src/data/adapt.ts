import { BYTES_IN_GB, BYTES_IN_GIB } from "@/lib/format";
import type { ProviderDto, TelemetryDto } from "./dto";
import type { Provider, StatusReason, Telemetry } from "./types";

function bytesOf(value: number | null | undefined, factor: number): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value * factor : null;
}

function adaptTelemetry(t: TelemetryDto): Telemetry {
  return {
    storageGitHash: t.storage_git_hash ?? null,
    providerGitHash: t.provider_git_hash ?? null,
    totalSpaceBytes: bytesOf(t.total_provider_space, BYTES_IN_GIB),
    usedSpaceBytes: bytesOf(t.used_provider_space, BYTES_IN_GIB),
    updatedAt: t.updated_at ?? null,
    cpuName: t.cpu_name ?? null,
    cpuCount: t.cpu_number ?? null,
    cpuVirtual: t.cpu_is_virtual ?? null,
    totalRamBytes: bytesOf(t.total_ram, BYTES_IN_GB),
    usageRamBytes: bytesOf(t.usage_ram, BYTES_IN_GB),
    diskRead: t.qd64_disk_read_speed ?? null,
    diskWrite: t.qd64_disk_write_speed ?? null,
    downloadSpeed: t.speedtest_download ?? null,
    uploadSpeed: t.speedtest_upload ?? null,
    ping: t.speedtest_ping ?? null,
    country: t.country ?? null,
    isp: t.isp ?? null,
  };
}

export function adaptProvider(dto: ProviderDto, nowSec: number): Provider {
  const reasons: StatusReason[] = (dto.statuses_reason_stats ?? []).map((r) => ({
    reason: r.reason,
    count: r.cnt,
  }));
  const updatedAt = dto.telemetry?.updated_at ?? null;
  return {
    pubkey: dto.pubkey,
    address: dto.address,
    status: dto.status,
    statusRatio: dto.status_ratio,
    location: dto.location
      ? {
          country: dto.location.country,
          countryIso: dto.location.country_iso,
          city: dto.location.city,
          timeZone: dto.location.time_zone,
        }
      : null,
    uptime: dto.uptime,
    workingTime: dto.working_time,
    rating: dto.rating,
    price: dto.price,
    minSpan: dto.min_span,
    maxSpan: dto.max_span,
    maxBagBytes: dto.max_bag_size_bytes,
    regTime: dto.reg_time,
    lastOnlineCheckTime: dto.last_online_check_time,
    hasTelemetry: dto.is_send_telemetry,
    telemetry: adaptTelemetry(dto.telemetry ?? {}),
    statusReasons: reasons,
    staleSec: dto.last_online_check_time ? Math.max(0, nowSec - dto.last_online_check_time) : 0,
    telemetryStaleSec: updatedAt ? Math.max(0, nowSec - updatedAt) : 0,
  };
}


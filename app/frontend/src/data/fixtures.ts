import { adaptProvider } from "./adapt";
import type { ProviderDto } from "./dto";
import type { Provider } from "./types";

// A real catalog row: disk in GiB, RAM in decimal GB, speed in bits, price in nano.
export const NOW = 1785545100;

export const baseDto: ProviderDto = {
  pubkey: "3a65231e59031a3a0c6f363030712730b11562a3c77556184c05d58adeb6b466",
  address: "EQAjRhPNqC9mY2muFNsYwYI5eqb-lsq-sD5xk3SLfrDljMwB",
  status: 0,
  status_ratio: 0.9977,
  location: { country: "Russia", country_iso: "RU", city: "Moscow", time_zone: "Europe/Moscow" },
  uptime: 99.717606,
  working_time: 27064916,
  rating: 20.415426,
  price: 10002432000,
  min_span: 604800,
  max_span: 6635520,
  max_bag_size_bytes: 85899345920,
  reg_time: 1758480100,
  last_online_check_time: 1785545007,
  is_send_telemetry: true,
  telemetry: {
    storage_git_hash: "ba05e00",
    provider_git_hash: "8c7ca5b",
    total_provider_space: 3820,
    used_provider_space: 3656.41,
    updated_at: 1785544962,
    cpu_name: "Intel(R) Xeon(R) CPU E5-2620 v2 @ 2.10GHz",
    cpu_number: 2,
    cpu_is_virtual: true,
    total_ram: 4.01,
    usage_ram: 1.14,
    qd64_disk_read_speed: "63.9MiB/s",
    qd64_disk_write_speed: "18.1MiB/s",
    speedtest_download: 1970199300,
    speedtest_upload: 1177201500,
    speedtest_ping: 15.970891,
    country: "RU",
    isp: "JSC IOT",
  },
  statuses_reason_stats: [
    { reason: 0, cnt: 432 },
    { reason: 401, cnt: 1 },
  ],
};

// The suffix keeps the key 64 chars long, so search and shortening behave as in the app.
export function providerWith(over: Partial<ProviderDto>, suffix = "aaaaaa"): Provider {
  return adaptProvider({ ...baseDto, ...over, pubkey: baseDto.pubkey.slice(0, 58) + suffix }, NOW);
}

export const stable = adaptProvider(baseDto, NOW);

export const overfilled = providerWith({
  rating: 16.33,
  telemetry: { ...baseDto.telemetry, total_provider_space: 4660, used_provider_space: 4659.18 },
});

export const silent = providerWith(
  {
    status: null,
    status_ratio: null,
    rating: 0,
    is_send_telemetry: false,
    telemetry: {},
    statuses_reason_stats: [],
    last_online_check_time: null,
  },
  "bbbbbb",
);

export const providers = [stable, overfilled, silent];

export interface TelemetryDto {
  storage_git_hash?: string | null;
  provider_git_hash?: string | null;
  total_provider_space?: number | null;
  used_provider_space?: number | null;
  updated_at?: number | null;
  cpu_name?: string | null;
  cpu_number?: number | null;
  cpu_is_virtual?: boolean | null;
  total_ram?: number | null;
  usage_ram?: number | null;
  qd64_disk_read_speed?: string | null;
  qd64_disk_write_speed?: string | null;
  speedtest_download?: number | null;
  speedtest_upload?: number | null;
  speedtest_ping?: number | null;
  country?: string | null;
  isp?: string | null;
}

interface LocationDto {
  country: string;
  country_iso: string;
  city: string;
  time_zone: string;
}

interface StatusReasonStatDto {
  reason: number;
  cnt: number;
}

export interface ProviderDto {
  status: number | null;
  location: LocationDto | null;
  status_ratio: number;
  pubkey: string;
  address: string;
  uptime: number;
  working_time: number;
  rating: number;
  max_span: number;
  price: number;
  min_span: number;
  max_bag_size_bytes: number;
  reg_time: number;
  last_online_check_time: number | null;
  is_send_telemetry: boolean;
  telemetry: TelemetryDto;
  statuses_reason_stats?: StatusReasonStatDto[];
}

export interface SearchRequest {
  filters: Record<string, unknown>;
  sort?: { column: string; order: "asc" | "desc" };
  exact: string[];
  limit: number;
  offset: number;
}

export interface SearchResponse {
  providers: ProviderDto[];
}

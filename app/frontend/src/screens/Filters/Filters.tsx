import { tick } from "@/lib/telegram";
import { BottomBar } from "@/components/BottomBar";
import { Card } from "@/components/Card";
import { Icon } from "@/components/Icon/Icon";
import { MainButton } from "@/components/MainButton";
import { RangeSlider } from "@/components/RangeSlider";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { SegmentControl } from "@/components/SegmentControl";
import { Toggle } from "@/components/Toggle";
import { selectCatalog } from "@/data/query";
import type { CatalogFilters, Provider, Range, SortField } from "@/data/types";
import { useT } from "@/i18n";
import type { DictStringKey } from "@/i18n/types";
import { cx } from "@/lib/cx";
import { useCatalog } from "@/stores/catalog";
import { useCatalogQuery } from "@/stores/catalogQuery";
import { useNames } from "@/stores/names";
import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Filters.module.css";

type SliderKey =
  | "rating"
  | "uptime"
  | "price"
  | "bag"
  | "cores"
  | "ram"
  | "age"
  | "minSpan"
  | "maxSpan"
  | "space"
  | "diskRead"
  | "diskWrite"
  | "download"
  | "upload"
  | "ping";

const SLIDER_META: Record<SliderKey, { labelKey: DictStringKey; dec: number; step: number; unit: string; unitKey?: DictStringKey }> = {
  rating: { labelKey: "ratingF", dec: 2, step: 0.01, unit: "" },
  uptime: { labelKey: "uptimeF", dec: 2, step: 0.01, unit: "%" },
  price: { labelKey: "priceF", dec: 2, step: 0.01, unit: "GRAM" },
  bag: { labelKey: "bagF", dec: 0, step: 1, unit: "GB" },
  cores: { labelKey: "coresF", dec: 0, step: 1, unit: "" },
  ram: { labelKey: "ramF", dec: 0, step: 1, unit: "GB" },
  age: { labelKey: "ageF", dec: 0, step: 1, unit: "", unitKey: "unitDays" },
  minSpan: { labelKey: "minSpanF", dec: 0, step: 1, unit: "", unitKey: "unitDays" },
  maxSpan: { labelKey: "maxSpanF", dec: 0, step: 1, unit: "", unitKey: "unitDays" },
  space: { labelKey: "spaceF", dec: 0, step: 10, unit: "GB" },
  diskRead: { labelKey: "diskReadF", dec: 0, step: 10, unit: "MiB/s" },
  diskWrite: { labelKey: "diskWriteF", dec: 0, step: 10, unit: "MiB/s" },
  download: { labelKey: "downloadF", dec: 0, step: 10, unit: "Mbit/s" },
  upload: { labelKey: "uploadF", dec: 0, step: 10, unit: "Mbit/s" },
  ping: { labelKey: "pingF", dec: 0, step: 1, unit: "ms" },
};

const SORT_FIELDS: SortField[] = ["rating", "uptime", "price", "working_time"];
const PROVIDER_SLIDERS: SliderKey[] = ["rating", "uptime", "price", "bag", "age", "minSpan", "maxSpan"];
const HARDWARE_SLIDERS: SliderKey[] = ["cores", "ram", "space", "diskRead", "diskWrite", "download", "upload", "ping"];

function FilterSlider({
  sliderKey,
  bounds,
  value,
  onChange,
}: {
  sliderKey: SliderKey;
  bounds: Range;
  value: Range;
  onChange: (value: Range) => void;
}) {
  const t = useT();
  const meta = SLIDER_META[sliderKey];
  const unit = meta.unitKey ? t[meta.unitKey] : meta.unit;
  const valueText = `${value[0].toFixed(meta.dec)} – ${value[1].toFixed(meta.dec)}${unit ? ` ${unit}` : ""}`;
  return (
    <div className={styles.sliderBlock}>
      <div className={styles.sliderHead}>
        <span className={styles.sliderLabel}>{t[meta.labelKey]}</span>
        <span className={styles.sliderValue}>{valueText}</span>
      </div>
      <RangeSlider value={value} min={bounds[0]} max={bounds[1]} step={meta.step} onChange={onChange} />
    </div>
  );
}

function ChipRow({
  options,
  value,
  anyLabel,
  mono,
  onChange,
}: {
  options: string[];
  value: string | null;
  anyLabel: string;
  mono?: boolean;
  onChange: (value: string | null) => void;
}) {
  return (
    <div className={styles.chips}>
      {[null, ...options].map((option) => {
        const active = value === option;
        return (
          <button
            key={option ?? "any"}
            type="button"
            className={cx(styles.chip, mono && option !== null && styles.chipMono, active && styles.chipActive)}
            onClick={() => {
              tick();
              onChange(option);
            }}
          >
            {option ?? anyLabel}
          </button>
        );
      })}
    </div>
  );
}

export function Filters() {
  const t = useT();
  const navigate = useNavigate();

  const providers = useCatalog((s) => s.providers);

  const names = useNames((s) => s.providers);
  const bounds = useCatalog((s) => s.bounds);
  const load = useCatalog((s) => s.load);

  const filters = useCatalogQuery((s) => s.filters);
  const sort = useCatalogQuery((s) => s.sort);
  const search = useCatalogQuery((s) => s.search);
  const setFilters = useCatalogQuery((s) => s.setFilters);
  const setSortField = useCatalogQuery((s) => s.setSortField);
  const resetFilters = useCatalogQuery((s) => s.resetFilters);

  useEffect(() => {
    void load();
  }, [load]);

  const locations = useMemo(() => {
    const set = new Set<string>();
    for (const provider of providers) {
      if (provider.location?.countryIso) set.add(provider.location.countryIso);
    }
    return [...set];
  }, [providers]);

  const hashes = useMemo(() => {
    const collect = (pick: (p: Provider) => string | null) => {
      const counts = new Map<string, number>();
      for (const provider of providers) {
        const hash = pick(provider);
        if (hash) counts.set(hash, (counts.get(hash) ?? 0) + 1);
      }
      return [...counts.keys()].sort((a, b) => (counts.get(b) ?? 0) - (counts.get(a) ?? 0));
    };
    return {
      storage: collect((p) => p.telemetry.storageGitHash),
      provider: collect((p) => p.telemetry.providerGitHash),
    };
  }, [providers]);

  const resultCount = useMemo(
    () => selectCatalog(providers, { favTab: false, search, filters, sort, favorites: [], names, bounds }).length,
    [providers, search, filters, sort, bounds],
  );

  const patch = (part: Partial<CatalogFilters>) => setFilters({ ...filters, ...part });
  const setRange = (key: SliderKey) => (range: Range) => patch({ [key]: range });

  const back = () => navigate(-1);

  const header = (
    <ScreenHeader
      title={t.filters}
      onBack={back}
      right={
        <button type="button" className={styles.reset} onClick={resetFilters}>
          {t.reset}
        </button>
      }
    />
  );

  if (!bounds) {
    return <Screen header={header}>{null}</Screen>;
  }

  return (
    <Screen
      header={header}
      bottom={
        <BottomBar>
          <MainButton label={t.showResults(resultCount)} onClick={back} />
        </BottomBar>
      }
    >
      <SectionHeader title={t.sortBy} />
      <Card>
        {SORT_FIELDS.map((field) => {
          const active = sort.field === field;
          return (
            <div
              key={field}
              className={cx(styles.sortRow, active && styles.sortRowActive)}
              onClick={() => {
                tick();
                setSortField(field);
              }}
            >
              <span className={cx(styles.sortLabel, active && styles.sortLabelActive)}>
                {t.sortField[field]}
              </span>
              {active && (
                <span className={cx(styles.sortChevron, sort.dir === "asc" && styles.sortChevronUp)}>
                  <Icon glyph="chevronDown" size={16} color="var(--ts-accent)" />
                </span>
              )}
            </div>
          );
        })}
      </Card>

      <SectionHeader title={t.providerGroup} />
      <Card className={styles.padCard}>
        {PROVIDER_SLIDERS.map((key) => (
          <FilterSlider
            key={key}
            sliderKey={key}
            bounds={bounds[key]}
            value={filters[key] ?? bounds[key]}
            onChange={setRange(key)}
          />
        ))}
        <div className={styles.subLabel}>{t.location}</div>
        <ChipRow
          options={locations}
          value={filters.location}
          anyLabel={t.anyLoc}
          onChange={(value) => patch({ location: value })}
        />
      </Card>

      <SectionHeader title={t.hardware} />
      <Card className={styles.padCard}>
        {HARDWARE_SLIDERS.map((key) => (
          <FilterSlider
            key={key}
            sliderKey={key}
            bounds={bounds[key]}
            value={filters[key] ?? bounds[key]}
            onChange={setRange(key)}
          />
        ))}
        <div className={styles.subLabel}>{t.cpuVirtual}</div>
        <div className={styles.segWrap}>
          <SegmentControl<boolean | null>
            options={[
              { value: null, label: t.any },
              { value: true, label: t.yes },
              { value: false, label: t.no },
            ]}
            value={filters.cpuVirtual}
            onChange={(value) => patch({ cpuVirtual: value })}
            height={33}
            fontSize={13.5}
          />
        </div>
      </Card>

      <SectionHeader title={t.software} />
      <Card className={styles.padCard}>
        <div className={styles.subLabel}>{t.storageHash}</div>
        <ChipRow
          options={hashes.storage}
          value={filters.storageHash}
          anyLabel={t.any}
          mono
          onChange={(value) => patch({ storageHash: value })}
        />
        <div className={styles.subLabel}>{t.providerHash}</div>
        <ChipRow
          options={hashes.provider}
          value={filters.providerHash}
          anyLabel={t.any}
          mono
          onChange={(value) => patch({ providerHash: value })}
        />
      </Card>

      <SectionHeader title={t.statusGroup} />
      <Card className={styles.padCard}>
        <div className={styles.toggleRow}>
          <span className={styles.toggleLabel}>{t.freeSpace}</span>
          <Toggle checked={filters.freeSpace} onChange={(value) => patch({ freeSpace: value })} ariaLabel={t.freeSpace} />
        </div>
        <div className={styles.subLabel}>{t.sendTelemetry}</div>
        <div className={styles.segWrap}>
          <SegmentControl<boolean | null>
            options={[
              { value: null, label: t.any },
              { value: true, label: t.yes },
              { value: false, label: t.no },
            ]}
            value={filters.telemetry}
            onChange={(value) => patch({ telemetry: value })}
            height={33}
            fontSize={13.5}
          />
        </div>
        <div className={styles.subLabel}>{t.statusF}</div>
        <SegmentControl<boolean>
          options={[
            { value: false, label: t.any },
            { value: true, label: t.stableOnly },
          ]}
          value={filters.stableOnly}
          onChange={(value) => patch({ stableOnly: value })}
          height={33}
          fontSize={13.5}
        />
      </Card>
    </Screen>
  );
}

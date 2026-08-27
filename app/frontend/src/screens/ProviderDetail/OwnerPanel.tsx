import { Chart } from "@/components/Chart";
import { Gauge } from "@/components/Gauge";
import { SectionHeader } from "@/components/SectionHeader";
import { SegmentControl } from "@/components/SegmentControl";
import { OWNER_CHART_RANGES, adaptOwner, type ChartKey, type GaugeKey, type OwnerChartRange, type OwnerPeriod } from "@/data/owner";
import { unsubscribeProvider } from "@/data/sync";
import type { Provider } from "@/data/types";
import { prefetchOwner, useOwnerData } from "@/hooks/useOwnerData";
import { useT } from "@/i18n";
import type { Dict, DictStringKey } from "@/i18n/types";
import { explorerAddressUrl } from "@/lib/address";
import { SC, tint } from "@/lib/colors";
import { cx } from "@/lib/cx";
import { JUST_NOW_SEC, formatTime } from "@/lib/format";
import { Icon } from "@/components/Icon/Icon";
import { useAlerts } from "@/stores/alerts";
import { useAuth } from "@/stores/auth";
import { useSettings } from "@/stores/settings";
import { type ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FieldCard } from "./FieldCard";
import styles from "./ProviderDetail.module.css";

type OwnerTab = "overview" | "earnings" | "charts";

const GAUGE_LABEL: Record<GaugeKey, DictStringKey> = {
  cpu_high: "chartCpu",
  ram_high: "chartRam",
  disk_load_high: "chartDisk",
  network_high: "chartNet",
};

const CHART_LABEL: Record<ChartKey, DictStringKey> = {
  cpu_high: "chartCpu",
  ram_high: "chartRam",
  disk_load_high: "chartDisk",
  net_in: "trafficIn",
  net_out: "trafficOut",
};

function balanceAge(secs: number, t: Dict): string {
  return secs < JUST_NOW_SEC ? t.updatedNow : t.updatedAgo(formatTime(secs, t, true));
}

export function OwnerPanel({ provider, pubkey, children }: { provider: Provider; pubkey: string; children: ReactNode }) {
  const t = useT();
  const navigate = useNavigate();
  const loggedIn = useAuth((s) => s.loggedIn);
  const thresholds = useAlerts((s) => s.thresholds);

  const [tab, setTab] = useState<OwnerTab>("overview");
  const [period, setPeriod] = useState<OwnerPeriod>("today");
  const [chartRange, setChartRange] = useState<OwnerChartRange>("1h");

  const { payload, denied, failed, refreshing } = useOwnerData(pubkey, loggedIn, period, chartRange);
  useEffect(() => {
    if (loggedIn) prefetchOwner(pubkey);
  }, [pubkey, loggedIn]);
  useEffect(() => {
    if (denied) unsubscribeProvider(pubkey);
  }, [denied, pubkey]);

  const owner = payload ? adaptOwner(provider, payload, thresholds) : null;
  const nowSec = Math.floor(Date.now() / 1000);
  const explorer = useSettings((state) => state.explorer);
  const walletUrl = explorerAddressUrl(provider.address, explorer);
  const loading = loggedIn && !payload && !denied && !failed;
  const problemBags = payload?.problem_bags ?? 0;

  return (
    <>
      {owner ? (
        <>
          <div className={cx(styles.card, styles.balanceCard)}>
            <div className={styles.balanceMain}>
              <div className={styles.subLabel}>{t.balanceLabel}</div>
              <div className={styles.balanceRow}>
                <span className={styles.balanceValue}>{owner.balance}</span>
                <span className={styles.balanceUnit}>GRAM</span>
              </div>
              <div className={styles.balanceUpdated}>
                {owner.balanceUpdatedAt === null ? t.unknown : balanceAge(nowSec - owner.balanceUpdatedAt, t)}
              </div>
            </div>
            <a
              className={styles.explorerBtn}
              href={walletUrl}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t.viewInExplorer}
            >
              <Icon glyph="arrowUpRight" size={20} stroke={2.2} />
            </a>
          </div>
          <div className={cx(styles.card, styles.storageCard)}>
            <div className={styles.storageTop}>
              <span className={styles.subLabel}>{t.storageUsage}</span>
              <span className={styles.storageValue}>
                {owner.usedSpace} / {owner.totalSpace}
              </span>
            </div>
            <div className={styles.storageBarRow}>
              <div className={styles.storageBarTrack}>
                <div className={styles.storageBarFill} style={{ width: `${owner.usedPct}%`, background: owner.barColor }} />
              </div>
              <span
                className={styles.storagePct}
                style={{
                  color: owner.spaceOver ? owner.barColor : "var(--ts-hint)",
                  fontWeight: owner.spaceOver ? 600 : 500,
                }}
              >
                {owner.usedPct}%
              </span>
            </div>
          </div>
          <button type="button" className={styles.bagsBtn} onClick={() => navigate(`/provider/${pubkey}/bags`)}>
            {t.bagsFailedTitle}
            <span className={styles.bagsTail}>
              {problemBags > 0 && (
                <span className={styles.bagsBadge} style={{ background: tint(SC.red, 0.16), color: SC.red }}>
                  {problemBags}
                </span>
              )}
              <Icon glyph="chevron" size={16} color="var(--ts-hint)" />
            </span>
          </button>
          <div className={styles.ownerSegWrap}>
            <SegmentControl<OwnerTab>
              options={[
                { value: "overview", label: t.overview },
                { value: "earnings", label: t.earningsTab },
                { value: "charts", label: t.chartsTab },
              ]}
              value={tab}
              onChange={setTab}
              height={36}
              fontSize={12}
            />
          </div>
        </>
      ) : loading ? (
        <>
          <div className={styles.card}>
            <div className={styles.skelBalanceLabel} />
            <div className={styles.skelBalanceValue} />
            <div className={styles.skelBalanceNote} />
          </div>
          <div className={cx(styles.card, styles.storageCard)}>
            <div className={styles.storageTop}>
              <div className={styles.skelStorageLabel} />
              <div className={styles.skelStorageValue} />
            </div>
            <div className={styles.skelStorageBar} />
          </div>
          <div className={styles.bagsBtn}>
            <div className={styles.skelBagsLabel} />
          </div>
          <div className={styles.ownerSegWrap}>
            <div className={styles.skelSeg} />
          </div>
        </>
      ) : null}

      {(tab === "overview" || !owner) && children}

      {tab === "earnings" && owner && (
        <>
          <div className={styles.summaryCard}>
            <div className={styles.periodWrap}>
              <PeriodSegment value={period} onChange={setPeriod} t={t} />
            </div>
            <SummaryRow label={t.earnedLabel} value={owner.summary.earned} loading={refreshing} />
            <SummaryRow label={t.trafficIn} value={owner.summary.trafficIn} loading={refreshing} />
            <SummaryRow label={t.trafficOut} value={owner.summary.trafficOut} loading={refreshing} />
            <SummaryRow label={t.storageGrowth} value={owner.summary.storageGrowth} loading={refreshing} />
          </div>
          <SectionHeader glyph="calendar" title={t.monthlyHeader} />
          <FieldCard
            rows={[
              { label: t.monthlyEarned, value: owner.monthly.earned },
              { label: t.monthlySpace, value: owner.monthly.space },
              { label: t.monthlyTraffic, value: owner.monthly.traffic },
            ]}
          />
          <SectionHeader glyph="history" title={t.allTimeHeader} />
          <FieldCard
            rows={[
              { label: t.allTimeEarned, value: owner.allTime.earned },
              { label: t.allTimeStored, value: owner.allTime.space },
              { label: t.allTimeTraffic, value: owner.allTime.traffic },
            ]}
          />
        </>
      )}

      {tab === "charts" && owner && (
        <>
          <div className={styles.gaugeGrid}>
            {owner.gauges.map((gauge) => (
              <Gauge key={gauge.key} value={gauge.value} threshold={gauge.threshold} label={t[GAUGE_LABEL[gauge.key]]} />
            ))}
          </div>
          <div className={styles.chartCard}>
            <SegmentControl<OwnerChartRange>
              options={OWNER_CHART_RANGES.map((range) => ({ value: range.value, label: t.hr(range.hours) }))}
              value={chartRange}
              onChange={setChartRange}
              height={34}
              fontSize={13}
            />
            {owner.charts.map((chart) => (
              <Chart
                key={chart.key}
                values={chart.values}
                peaks={chart.peaks}
                times={chart.times}
                threshold={chart.threshold}
                unit={chart.unit}
                current={chart.current}
                label={t[CHART_LABEL[chart.key]]}
                loading={refreshing}
              />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function SummaryRow({ label, value, loading }: { label: string; value: string; loading?: boolean }) {
  return (
    <div className={styles.summaryRow}>
      <span className={styles.summaryLabel}>{label}</span>
      {loading ? <span className={styles.skelValue} /> : <span>{value}</span>}
    </div>
  );
}

function PeriodSegment({ value, onChange, t }: { value: OwnerPeriod; onChange: (value: OwnerPeriod) => void; t: Dict }) {
  return (
    <SegmentControl<OwnerPeriod>
      options={[
        { value: "hour", label: t.periodHour },
        { value: "today", label: t.periodDay },
        { value: "week", label: t.periodWeek },
        { value: "month", label: t.periodMonth },
      ]}
      value={value}
      onChange={onChange}
      height={34}
      fontSize={12.5}
    />
  );
}

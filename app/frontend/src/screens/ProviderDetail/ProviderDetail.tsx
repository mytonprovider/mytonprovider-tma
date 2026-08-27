import { BottomBar } from "@/components/BottomBar";
import { Card } from "@/components/Card";
import { ConfirmSheet } from "@/components/ConfirmSheet";
import { CopyRow } from "@/components/CopyRow";
import { ExplorerAddressRow } from "@/components/ExplorerAddressRow";
import { FieldRow } from "@/components/FieldRow";
import { Icon } from "@/components/Icon/Icon";
import { MainButton } from "@/components/MainButton";
import { MetricTile } from "@/components/MetricTile";
import { NameSheet } from "@/components/NameSheet";
import { PasswordSheet } from "@/components/PasswordSheet";
import { ProviderHeader } from "@/components/ProviderHeader";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusDot } from "@/components/StatusDot";
import { unsubscribeProvider } from "@/data/sync";
import type { Provider } from "@/data/types";
import { useLogin } from "@/hooks/useLogin";
import { useT } from "@/i18n";
import type { Dict } from "@/i18n/types";
import { toUserFriendly } from "@/lib/address";
import { SC, rankColor, tint } from "@/lib/colors";
import { cx } from "@/lib/cx";
import { EMPTY, ago, amount, formatBytes, formatDiskSpeed, formatMbits, formatPing, formatPrice, formatPriceGram, formatSpace, formatTime, shorten, uptimeTone } from "@/lib/format";
import { describeStatus } from "@/lib/status";
import { useAuth } from "@/stores/auth";
import { useCatalog } from "@/stores/catalog";
import { useNames } from "@/stores/names";
import { useSubscriptions } from "@/stores/subscriptions";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { type Field, FieldCard } from "./FieldCard";
import { OwnerPanel } from "./OwnerPanel";
import styles from "./ProviderDetail.module.css";
import { TriggerBanners } from "./TriggerBanners";

function placeOf(p: Provider, t: Dict): string {
  if (!p.location) return t.unknown;
  return p.location.city ? `${p.location.city}, ${p.location.country}` : p.location.country || t.unknown;
}

function providerFields(p: Provider, t: Dict): Field[] {
  return [
    { label: t.span, value: `${formatTime(p.minSpan, t)} – ${formatTime(p.maxSpan, t)}` },
    { label: t.maxBag, value: formatBytes(p.maxBagBytes) },
    { label: t.workingTime, value: formatTime(p.workingTime, t) },
    { label: t.lastOnline, value: p.lastOnlineCheckTime === null ? t.unknown : ago(p.staleSec, t) },
    ...(p.hasTelemetry
      ? [
          {
            label: t.telemetryField,
            value: p.telemetry.updatedAt === null ? t.unknown : ago(p.telemetryStaleSec, t),
          },
        ]
      : []),
    { label: t.location, value: placeOf(p, t) },
    { label: t.uptime, value: `${amount(p.uptime)} %` },
    { label: t.rating, value: amount(p.rating) },
    { label: t.price, value: formatPriceGram(p.price) },
  ];
}

function hardwareFields(p: Provider, t: Dict): Field[] {
  const tel = p.telemetry;
  const ram =
    tel.usageRamBytes != null && tel.totalRamBytes != null
      ? `${formatSpace(tel.usageRamBytes)} / ${formatSpace(tel.totalRamBytes)}`
      : EMPTY;
  const space =
    tel.usedSpaceBytes != null && tel.totalSpaceBytes != null
      ? `${formatSpace(tel.usedSpaceBytes)} / ${formatSpace(tel.totalSpaceBytes)}`
      : EMPTY;
  return [
    { label: t.cpuName, value: tel.cpuName ?? EMPTY },
    { label: t.cpuNumber, value: tel.cpuCount != null ? String(tel.cpuCount) : EMPTY },
    { label: t.cpuVirtual, value: tel.cpuVirtual == null ? EMPTY : tel.cpuVirtual ? t.yes : t.no },
    { label: t.ram, value: ram },
    { label: t.totalSpace, value: space },
  ];
}

function networkFields(p: Provider, t: Dict): Field[] {
  const tel = p.telemetry;
  return [
    { label: t.stDownload, value: formatMbits(tel.downloadSpeed) },
    { label: t.stUpload, value: formatMbits(tel.uploadSpeed) },
    { label: t.stPing, value: formatPing(tel.ping) },
    { label: t.country, value: tel.country ?? t.unknown },
    { label: t.isp, value: tel.isp ?? EMPTY },
  ];
}

export function ProviderDetail() {
  const t = useT();
  const navigate = useNavigate();
  const { pubkey = "" } = useParams();

  const providers = useCatalog((s) => s.providers);
  const ranks = useCatalog((s) => s.ranks);
  const status = useCatalog((s) => s.status);
  const load = useCatalog((s) => s.load);

  const loggedIn = useAuth((s) => s.loggedIn);
  const { start: startLogin } = useLogin();
  const isSubscribed = useSubscriptions((s) => s.subscribed.includes(pubkey));
  const name = useNames((s) => s.providers[pubkey]);

  const [pwOpen, setPwOpen] = useState(false);
  const [nameOpen, setNameOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    void load();
  }, [load]);

  const provider = providers.find((p) => p.pubkey === pubkey);
  const rank = ranks[pubkey];

  useEffect(() => {
    if (status === "ready" && !provider) navigate("/", { replace: true });
  }, [status, provider, navigate]);

  const back = () => navigate(-1);

  if (!provider) {
    return <Screen header={<ScreenHeader title="" onBack={back} />}>{null}</Screen>;
  }

  const st = describeStatus(provider, t);
  const hasTelemetry = provider.hasTelemetry;

  const subscribeLabel = isSubscribed ? t.unsubscribe : loggedIn ? t.subscribe : t.loginTg;
  const onSubscribe = () => {
    if (!loggedIn) return startLogin();
    if (isSubscribed) return setConfirmOpen(true);
    setPwOpen(true);
  };

  const header = <ProviderHeader pubkey={provider.pubkey} color={st.color} onBack={back} />;

  const overview = (
    <>
      <div className={styles.overviewCard}>
        <FieldRow
          label={t.nameField}
          value={
            <button type="button" aria-label={t.nameEdit} className={styles.nameBtn} onClick={() => setNameOpen(true)}>
              <span className={name ? styles.nameValue : styles.nameSet}>{name || t.nameSet}</span>
              <Icon glyph="edit" size={16} color="var(--ts-hint)" />
            </button>
          }
        />
        <CopyRow label={t.publicKey} copyValue={provider.pubkey} divider>
          <span className={cx(styles.mono, styles.monoText)}>{shorten(provider.pubkey, 12)}</span>
        </CopyRow>
        <ExplorerAddressRow label={t.address} address={toUserFriendly(provider.address)} divider />
        {providerFields(provider, t).map((field, index) => (
          <FieldRow key={index} label={field.label} value={field.value} divider />
        ))}
      </div>

      {hasTelemetry ? (
        <>
          <SectionHeader glyph="cpu" title={t.hardware} />
          <FieldCard rows={hardwareFields(provider, t)} />
          <SectionHeader glyph="bars" title={t.benchmarks} />
          <FieldCard
            rows={[
              { label: t.diskRead, value: formatDiskSpeed(provider.telemetry.diskRead) },
              { label: t.diskWrite, value: formatDiskSpeed(provider.telemetry.diskWrite) },
            ]}
          />
          <SectionHeader glyph="globe" title={t.network} />
          <FieldCard rows={networkFields(provider, t)} />
          <SectionHeader glyph="server" title={t.software} />
          <Card>
            <CopyRow label={t.storageHash} copyValue={provider.telemetry.storageGitHash}>
              <span className={cx(styles.mono, styles.monoText)}>{provider.telemetry.storageGitHash ?? EMPTY}</span>
            </CopyRow>
            <CopyRow label={t.providerHash} copyValue={provider.telemetry.providerGitHash} divider>
              <span className={cx(styles.mono, styles.monoText)}>{provider.telemetry.providerGitHash ?? EMPTY}</span>
            </CopyRow>
          </Card>
        </>
      ) : (
        <div className={styles.noTelemetry}>
          <Icon glyph="clock" size={16} color="var(--ts-hint)" />
          <span className={styles.noTelemetryText}>{t.noTelemetry}</span>
        </div>
      )}
    </>
  );

  return (
    <>
      <Screen
        header={header}
        bottom={
          <BottomBar>
            <MainButton label={subscribeLabel} tone={isSubscribed ? "destructive" : "accent"} onClick={onSubscribe} />
          </BottomBar>
        }
      >
        <TriggerBanners pubkey={pubkey} />

        <div className={styles.statusCard}>
          {st.total > 0 && (
            <div className={styles.health}>
              <div style={{ flexGrow: Math.max(st.ratio, 0.0001), background: st.color }} />
              <div style={{ flexGrow: Math.max(1 - st.ratio, 0), background: "var(--ts-sepf)" }} />
            </div>
          )}
          <div className={styles.statusBody}>
            <div className={styles.statusTop}>
              <div className={styles.statusLabelWrap} style={{ color: st.color }}>
                <StatusDot color={st.color} size={9} />
                <span>{st.label}</span>
                {st.hasRatio && <span className={styles.statusRatio}>{amount(st.ratio * 100)}%</span>}
              </div>
              {st.total > 0 && (
                <div className={styles.checks}>
                  <span className={styles.checksLabel}>{t.filesAvail}</span>
                  <span className={styles.passedBadge} style={{ background: tint(st.checksColor, 0.18), color: st.checksColor }}>
                    {st.passed}
                  </span>
                  <span className={styles.slash}>/</span>
                  <span className={styles.totalBadge}>{st.total}</span>
                </div>
              )}
            </div>
          </div>
          {st.desc && (
            <div className={styles.statusFooter}>
              <span className={styles.statusDesc}>{st.desc}</span>
            </div>
          )}
        </div>

        <div className={styles.tiles}>
          <MetricTile
            value={amount(provider.rating)}
            label={
              rank ? (
                <>
                  {t.rating} <b className={styles.mark} style={{ color: rankColor(rank) }}>{`#${rank}`}</b>
                </>
              ) : (
                t.rating
              )
            }
            valueColor="var(--ts-accent)"
          />
          <MetricTile value={amount(provider.uptime)} unit="%" label={t.uptime} valueColor={SC[uptimeTone(provider.uptime)]} />
          <MetricTile value={formatPrice(provider.price)} unit="GRAM" label={t.priceUnit} />
        </div>

        {isSubscribed ? (
          <OwnerPanel provider={provider} pubkey={pubkey}>
            {overview}
          </OwnerPanel>
        ) : (
          overview
        )}
      </Screen>
      {pwOpen && <PasswordSheet pubkey={pubkey} onClose={() => setPwOpen(false)} />}
      {nameOpen && (
        <NameSheet
          kind="provider"
          target={pubkey}
          subtitle={shorten(provider.pubkey, 14).toUpperCase()}
          onClose={() => setNameOpen(false)}
        />
      )}
      {confirmOpen && (
        <ConfirmSheet
          title={t.unsubscribeConfirm}
          subtitle={name || shorten(provider.pubkey, 14).toUpperCase()}
          confirmLabel={t.unsubscribe}
          onConfirm={() => unsubscribeProvider(pubkey)}
          onClose={() => setConfirmOpen(false)}
        />
      )}
    </>
  );
}

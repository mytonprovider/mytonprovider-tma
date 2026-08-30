import { Card } from "@/components/Card";
import { CopyRow } from "@/components/CopyRow";
import { Callout } from "@/components/Callout";
import { Field } from "@/components/Field";
import { ExplorerAddressRow } from "@/components/ExplorerAddressRow";
import { FieldRow } from "@/components/FieldRow";
import { Icon } from "@/components/Icon/Icon";
import { MetricTile } from "@/components/MetricTile";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { BackendError, backend, type BagPayload, type BagProvider } from "@/data/backend";
import type { Provider } from "@/data/types";
import { useT } from "@/i18n";
import type { Dict } from "@/i18n/types";
import { ADDRESS_RE, RAW_RE, toUserFriendly } from "@/lib/address";
import { SC } from "@/lib/colors";
import { EMPTY, ago, formatBytes, formatCount, formatPriceGram, formatTime, shorten } from "@/lib/format";
import { bagGatewayUrl } from "@/lib/gateway";
import { reasonText, reasonTone, stateText, stateTone } from "@/lib/status";
import { useCatalog } from "@/stores/catalog";
import { useNames } from "@/stores/names";
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import styles from "./BagExplorer.module.css";

const REPORT_BOT = "https://t.me/bagidreport_bot";
// Catalogue quotes per 200 GB per month, the contract per MB per day - same divisor as the backend.
const PRICE_MB_DAYS = 200 * 1024 * 30;
const BAG_ID_RE = /^[0-9a-fA-F]{64}$/;

type QueryKind = "bag" | "address";

function classify(query: string): QueryKind | null {
  if (BAG_ID_RE.test(query)) return "bag";
  if (RAW_RE.test(query) || ADDRESS_RE.test(query)) return "address";
  return null;
}

async function resolveBag(query: string, kind: QueryKind): Promise<BagPayload | null> {
  const search = kind === "bag" ? query.toLowerCase() : query;
  try {
    return await backend.bag(search);
  } catch (error) {
    if (error instanceof BackendError && error.status === 404) return null;
    throw error;
  }
}

// A running contract was signed on older terms, so only a hire that never happened is flagged.
function mismatch(prov: BagProvider, listed: Provider | undefined): { span: boolean; rate: boolean } {
  if (prov.state !== "not_accepted" || !listed) return { span: false, rate: false };
  return {
    span:
      prov.payment_max_span !== null &&
      (prov.payment_max_span < listed.minSpan || prov.payment_max_span > listed.maxSpan),
    rate: prov.rate_per_mb_day !== null && prov.rate_per_mb_day < Math.round(listed.price / PRICE_MB_DAYS),
  };
}

// Same thresholds the provider card uses for its own ratio.
function ratioTone(passed: number, total: number): "green" | "yellow" | "red" {
  const ratio = total > 0 ? passed / total : 0;
  return ratio >= 0.99 ? "green" : ratio >= 0.8 ? "yellow" : "red";
}

// The window closing is not the alarm - the ladder gives proofs OVERDUE_FACTOR of slack
// because they reach the chain late, so the row turns red with the state, not before it.
function nextProofValue(
  lastProof: number | null,
  maxSpan: number | null,
  nowSec: number,
  t: Dict,
  notConfirmed: boolean,
): ReactNode {
  if (!lastProof || !maxSpan) return EMPTY;
  const deadline = lastProof + maxSpan;
  if (deadline <= nowSec) {
    const late = ago(nowSec - deadline, t);
    return notConfirmed ? <span style={{ color: SC.red }}>{late}</span> : late;
  }
  return t.inFuture(formatTime(deadline - nowSec, t, true));
}

type Status = "idle" | "loading" | "ready" | "notfound" | "invalid" | "failed";

export function BagExplorer() {
  const t = useT();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const providers = useCatalog((s) => s.providers);
  const names = useNames((s) => s.providers);
  const load = useCatalog((s) => s.load);

  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<BagPayload | null>(null);
  const reqRef = useRef(0);

  useEffect(() => {
    void load();
  }, [load]);

  const runSearch = useCallback((raw: string) => {
    const q = raw.trim();
    if (!q) return;
    const kind = classify(q);
    if (!kind) {
      setResult(null);
      setStatus("invalid");
      return;
    }
    const id = ++reqRef.current;
    setStatus("loading");
    resolveBag(q, kind)
      .then((res) => {
        if (reqRef.current !== id) return;
        setResult(res);
        setStatus(res ? "ready" : "notfound");
      })
      .catch((error: unknown) => {
        if (reqRef.current !== id) return;
        console.error("bag lookup failed", error);
        setStatus("failed");
      });
  }, []);

  useEffect(() => {
    const q = params.get("q");
    if (q) {
      setQuery(q);
      runSearch(q);
    }
  }, [params, runSearch]);

  const header = <ScreenHeader title={t.explorerTitle} onBack={() => navigate(-1)} />;
  const nowSec = Math.floor(Date.now() / 1000);
  const slots = result?.providers ?? [];
  const confirmed = slots.filter((p) => p.state === "confirmed").length;
  const passed = slots.filter((p) => p.reason === 0).length;
  // Upstream checks the whole network in one batch, so the age is one per bag, not per slot.
  const checkedAt = slots.reduce<number | null>((max, p) => (p.reason_at ?? 0) > (max ?? 0) ? p.reason_at : max, null);

  return (
    <Screen header={header}>
      <Field
        glyph="search"
        className={styles.search}
        value={query}
        onChange={(next) => {
          setQuery(next);
          if (status === "invalid") setStatus("idle");
        }}
        placeholder={t.bagSearchPlaceholder}
        enterKeyHint="search"
        invalid={status === "invalid"}
        onEnter={() => runSearch(query)}
        trailing={
          query && (
            <button
              type="button"
              aria-label="Clear"
              className={styles.searchClear}
              onClick={() => {
                setQuery("");
                setStatus("idle");
                setResult(null);
              }}
            >
              <Icon glyph="close" size={16} color="var(--ts-hint)" stroke={2} />
            </button>
          )
        }
      />

      {status === "idle" && <Callout glyph="search" title={t.bagIdleTitle} desc={t.bagIdleDesc} />}
      {status === "loading" && <BagSkeleton t={t} />}
      {status === "invalid" && (
        <Callout glyph="info" title={t.bagInvalidTitle} desc={t.bagInvalidDesc} iconColor="var(--ts-hint)" />
      )}
      {status === "notfound" && (
        <Callout glyph="close" title={t.bagNotFoundTitle} desc={t.bagNotFoundDesc} iconColor="var(--ts-hint)" />
      )}
      {status === "failed" && <Callout glyph="close" title={t.bagsLoadError} iconColor="var(--ts-hint)" />}

      {status === "ready" && result && (
        <>
          <Card className={styles.stateCard}>
            <div className={styles.title} style={{ color: SC[stateTone(result.state)] }}>
              {stateText(result.state, t)}
            </div>
          </Card>
          <div className={styles.tiles}>
            <MetricTile
              value={
                <>
                  {confirmed}
                  <span className={styles.den}>
                    <span className={styles.slash}>/</span>
                    {result.providers.length}
                  </span>
                </>
              }
              label={t.bagProofs}
              valueColor={SC[ratioTone(confirmed, result.providers.length)]}
            />
            <MetricTile
              value={
                checkedAt === null ? (
                  EMPTY
                ) : (
                  <>
                    {passed}
                    <span className={styles.den}>
                      <span className={styles.slash}>/</span>
                      {result.providers.length}
                    </span>
                  </>
                )
              }
              label={checkedAt === null ? t.bagChecks : `${t.bagChecks} · ${ago(nowSec - checkedAt, t)}`}
              valueColor={checkedAt === null ? "var(--ts-hint)" : SC[ratioTone(passed, result.providers.length)]}
            />
          </div>
          <SectionHeader title={t.bagSection} />
          <Card>
            {result.bag_id && (
              <CopyRow label={t.bagId} copyValue={result.bag_id}>
                <a
                  className={styles.link}
                  href={bagGatewayUrl(result.bag_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {shorten(result.bag_id, 12).toUpperCase()}
                </a>
              </CopyRow>
            )}
            <FieldRow divider label={t.bagSize} value={formatBytes(result.size)} />
            <FieldRow divider label={t.bagChunk} value={formatBytes(result.chunk_size)} />
            {result.merkle_hash && (
              <CopyRow label={t.bagMerkle} copyValue={result.merkle_hash} divider>
                <span className={styles.mono}>{shorten(result.merkle_hash, 12)}</span>
              </CopyRow>
            )}
            <FieldRow divider label={t.bagDepth} value={result.key_len ?? EMPTY} />
          </Card>

          <SectionHeader title={t.bagContract} />
          <Card>
            <ExplorerAddressRow label={t.bagAddress} address={result.contract_address} />
            {result.owner_address && (
              <ExplorerAddressRow label={t.bagOwner} address={toUserFriendly(result.owner_address)} divider />
            )}
            <FieldRow
              divider
              label={t.balanceLabel}
              value={result.balance != null ? formatPriceGram(result.balance) : EMPTY}
            />
          </Card>

          <div className={styles.count}>
            {t.list} · {result.providers.length}
          </div>
          <div className={styles.list}>
            {result.providers.map((prov) => {
              const listed = providers.find((p) => p.pubkey === prov.pubkey);
              const off = mismatch(prov, listed);
              return (
                <Card key={prov.pubkey}>
                  <div className={styles.title} style={{ color: SC[stateTone(prov.state)] }}>
                    {stateText(prov.state, t)}
                  </div>
                  <div
                    className={styles.sub}
                    style={prov.reason ? { color: SC[reasonTone(prov.reason)] } : undefined}
                  >
                    {reasonText(prov.reason, t)}
                  </div>
                  <CopyRow label={t.bagProvider} copyValue={prov.pubkey} divider compact>
                    <span className={styles.pk}>
                      {names[prov.pubkey] || shorten(prov.pubkey, 16).toUpperCase()}
                    </span>
                  </CopyRow>
                  <FieldRow
                    divider
                    compact
                    label={t.maxSpanF}
                    value={
                      <>
                        <span style={off.span ? { color: SC.red } : undefined}>
                          {prov.payment_max_span !== null ? formatTime(prov.payment_max_span, t) : EMPTY}
                        </span>
                        <span className={styles.slash}>/</span>
                        {listed ? formatTime(listed.maxSpan, t) : EMPTY}
                      </>
                    }
                  />
                  <FieldRow
                    divider
                    compact
                    label={t.bagRate}
                    value={
                      <>
                        <span style={off.rate ? { color: SC.red } : undefined}>
                          {prov.rate_per_mb_day !== null ? formatCount(prov.rate_per_mb_day) : EMPTY}
                        </span>
                        <span className={styles.slash}>/</span>
                        {listed ? formatCount(Math.round(listed.price / PRICE_MB_DAYS)) : EMPTY}
                      </>
                    }
                  />
                  <FieldRow
                    divider
                    compact
                    label={t.lastProof}
                    value={prov.last_proof_at ? ago(nowSec - prov.last_proof_at, t) : EMPTY}
                  />
                  <FieldRow
                    divider
                    compact
                    label={t.nextProof}
                    value={nextProofValue(
                      prov.last_proof_at,
                      prov.payment_max_span,
                      nowSec,
                      t,
                      prov.state === "not_confirmed",
                    )}
                  />
                  <CopyRow label={t.bagNextByte} copyValue={String(prov.next_proof_byte ?? "")} divider compact>
                    <span className={styles.mono}>
                      {prov.next_proof_byte !== null ? formatCount(prov.next_proof_byte) : EMPTY}
                    </span>
                  </CopyRow>
                  <CopyRow label={t.bagNonce} copyValue={prov.nonce ?? ""} divider compact>
                    <span className={styles.mono}>{prov.nonce ?? EMPTY}</span>
                  </CopyRow>
                </Card>
              );
            })}
          </div>
          <a className={styles.report} href={REPORT_BOT} target="_blank" rel="noopener noreferrer">
            <Icon glyph="warn" size={15} color="var(--ts-danger)" />
            {t.bagReport}
          </a>
        </>
      )}
    </Screen>
  );
}

function BagSkeleton({ t }: { t: Dict }) {
  const row = (i: number, valueClass: string) => (
    <FieldRow
      key={i}
      divider={i > 0}
      label={<span className={styles.skLabel} />}
      value={<span className={valueClass} />}
    />
  );
  return (
    <>
      {/* Same order the loaded screen has, or the layout jumps once the answer arrives. */}
      <Card className={styles.stateCard}>
        <div className={styles.title}>
          <span className={styles.skTitle} />
        </div>
      </Card>
      <div className={styles.tiles}>
        {[0, 1].map((key) => (
          <div key={key} className={styles.skTile}>
            <span className={styles.skValueNarrow} />
          </div>
        ))}
      </div>
      <SectionHeader title={t.bagSection} />
      <Card>
        {row(0, styles.skValueWide)}
        {row(1, styles.skValueMid)}
        {row(2, styles.skValueMid)}
        {row(3, styles.skValueWide)}
        {row(4, styles.skValueNarrow)}
      </Card>
      <SectionHeader title={t.bagContract} />
      <Card>
        {row(0, styles.skValueWide)}
        {row(1, styles.skValueWide)}
        {row(2, styles.skValueNarrow)}
        {row(3, styles.skValueNarrow)}
      </Card>
      <div className={styles.count}>
        <span className={styles.countBar} />
      </div>
      <div className={styles.list}>
        {[0, 1].map((key) => (
          <Card key={key}>
            <div className={styles.title}>
              <span className={styles.skTitle} />
            </div>
            <div className={styles.sub}>
              <span className={styles.skSub} />
            </div>
            {row(0, styles.skValueMid)}
            {row(1, styles.skValueMid)}
            {row(2, styles.skValueWide)}
            {row(3, styles.skValueMid)}
            {row(4, styles.skValueMid)}
            {row(5, styles.skValueWide)}
          </Card>
        ))}
      </div>
    </>
  );
}

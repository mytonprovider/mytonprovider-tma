import { Card } from "@/components/Card";
import { CopyButton } from "@/components/CopyButton";
import { CopyRow } from "@/components/CopyRow";
import { Callout } from "@/components/Callout";
import { Field } from "@/components/Field";
import { ExplorerAddressRow } from "@/components/ExplorerAddressRow";
import { FieldRow } from "@/components/FieldRow";
import { Icon } from "@/components/Icon/Icon";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusDot } from "@/components/StatusDot";
import { BackendError, backend, type BagPayload } from "@/data/backend";
import { type StorageContract, readStorageContract } from "@/data/toncenter";
import { useT } from "@/i18n";
import type { Dict } from "@/i18n/types";
import { ADDRESS_RE, RAW_RE, toUserFriendly } from "@/lib/address";
import { SC, tint } from "@/lib/colors";
import { EMPTY, ago, formatBytes, formatPriceGram, formatTime, shorten } from "@/lib/format";
import { bagGatewayUrl } from "@/lib/gateway";
import { reasonText, reasonTone } from "@/lib/status";
import { useCatalog } from "@/stores/catalog";
import { useNames } from "@/stores/names";
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import styles from "./BagExplorer.module.css";

const REPORT_BOT = "https://t.me/bagidreport_bot";
const BAG_ID_RE = /^[0-9a-fA-F]{64}$/;

type QueryKind = "bag" | "address";

function classify(query: string): QueryKind | null {
  if (BAG_ID_RE.test(query)) return "bag";
  if (RAW_RE.test(query) || ADDRESS_RE.test(query)) return "address";
  return null;
}

interface Resolved {
  address: string;
  owner: string | null;
  reasons: Map<string, number | null>;
  chain: StorageContract;
}

async function resolveBag(query: string, kind: QueryKind): Promise<Resolved | null> {
  const search = kind === "bag" ? query.toLowerCase() : query;
  let db: BagPayload | null = null;
  try {
    db = await backend.bag(search);
  } catch (error) {
    if (!(error instanceof BackendError && error.status === 404)) throw error;
  }
  if (kind === "bag" && !db) return null;
  const address = kind === "bag" && db ? db.contract_address : search;
  const chain = await readStorageContract(address);
  if (!chain) return null;
  const reasons = new Map((db?.providers ?? []).map((p) => [p.pubkey, p.reason]));
  return { address, owner: db?.owner_address ?? null, reasons, chain };
}

function providerStatus(reason: number | null, t: Dict): { color: string; label: string; code: number | null } {
  if (reason === null) return { color: SC.gray, label: t.notTracked, code: null };
  if (reason === 0) return { color: SC.green, label: t.status.stable, code: null };
  return { color: SC[reasonTone(reason)], label: reasonText(reason, t), code: reason };
}

function nextProofValue(lastProof: number, maxSpan: number, nowSec: number, t: Dict): ReactNode {
  if (lastProof <= 0) return EMPTY;
  const deadline = lastProof + maxSpan;
  if (deadline <= nowSec) {
    return <span style={{ color: SC.red }}>{ago(nowSec - deadline, t)}</span>;
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
  const [result, setResult] = useState<Resolved | null>(null);
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
          <SectionHeader title={t.bagSection} />
          <Card>
            <CopyRow label={t.bagId} copyValue={result.chain.bagId}>
              <a
                className={styles.link}
                href={bagGatewayUrl(result.chain.bagId)}
                target="_blank"
                rel="noopener noreferrer"
              >
                {shorten(result.chain.bagId, 12).toUpperCase()}
              </a>
            </CopyRow>
            <FieldRow divider label={t.bagSize} value={formatBytes(result.chain.fileSize)} />
            <FieldRow divider label={t.bagChunk} value={formatBytes(result.chain.chunkSize)} />
            <CopyRow label={t.bagMerkle} copyValue={result.chain.merkleHash} divider>
              <span className={styles.mono}>{shorten(result.chain.merkleHash, 12)}</span>
            </CopyRow>
          </Card>

          <SectionHeader title={t.bagContract} />
          <Card>
            <ExplorerAddressRow label={t.bagAddress} address={result.address} />
            {result.owner && <ExplorerAddressRow label={t.bagOwner} address={toUserFriendly(result.owner)} divider />}
            <FieldRow divider label={t.balanceLabel} value={formatPriceGram(result.chain.balance)} />
            <FieldRow
              divider
              label={t.peers}
              value={
                <>
                  {result.chain.providers.filter((p) => result.reasons.get(p.pubkey) === 0).length}
                  <span className={styles.slash}>/</span>
                  {result.chain.providers.length}
                </>
              }
            />
          </Card>

          <div className={styles.count}>
            {t.list} · {result.chain.providers.length}
          </div>
          <div className={styles.list}>
            {result.chain.providers.map((prov) => {
              const st = providerStatus(result.reasons.get(prov.pubkey) ?? null, t);
              const offer = providers.find((p) => p.pubkey === prov.pubkey)?.maxSpan ?? null;
              const spanMismatch = offer !== null && offer < prov.maxSpan;
              return (
                <Card key={prov.pubkey}>
                  <div className={styles.phead}>
                    <span className={styles.pk}>{names[prov.pubkey] || shorten(prov.pubkey, 16).toUpperCase()}</span>
                    <CopyButton value={prov.pubkey} />
                  </div>
                  <div className={styles.pstat}>
                    <StatusDot color={st.color} size={7} />
                    <span className={styles.plabel} style={{ color: st.color }}>
                      {st.label}
                    </span>
                    {st.code !== null && (
                      <span className={styles.badge} style={{ color: st.color, background: tint(st.color, 0.15) }}>
                        {st.code}
                      </span>
                    )}
                  </div>
                  <FieldRow
                    divider
                    label={t.maxSpanF}
                    value={
                      <>
                        <span style={spanMismatch ? { color: SC.red } : undefined}>{formatTime(prov.maxSpan, t)}</span>
                        <span className={styles.slash}>/</span>
                        {offer !== null ? formatTime(offer, t) : EMPTY}
                      </>
                    }
                  />
                  <FieldRow
                    divider
                    label={t.lastProof}
                    value={prov.lastProof > 0 ? ago(nowSec - prov.lastProof, t) : EMPTY}
                  />
                  <FieldRow divider label={t.nextProof} value={nextProofValue(prov.lastProof, prov.maxSpan, nowSec, t)} />
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
      <SectionHeader title={t.bagSection} />
      <Card>
        {row(0, styles.skValueWide)}
        {row(1, styles.skValueMid)}
        {row(2, styles.skValueMid)}
        {row(3, styles.skValueWide)}
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
            <div className={styles.phead}>
              <span className={styles.skPk} />
            </div>
            <div className={styles.pstat}>
              <span className={styles.skStatusBar} />
            </div>
            {row(0, styles.skValueMid)}
            {row(1, styles.skValueWide)}
            {row(2, styles.skValueMid)}
          </Card>
        ))}
      </div>
    </>
  );
}

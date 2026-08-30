import { Callout } from "@/components/Callout";
import { CopyRow } from "@/components/CopyRow";
import { ExplorerAddressRow } from "@/components/ExplorerAddressRow";
import { Field } from "@/components/Field";
import { FieldRow } from "@/components/FieldRow";
import { LoadMore } from "@/components/LoadMore";
import { ProviderHeader } from "@/components/ProviderHeader";
import { Screen } from "@/components/Screen";
import { StatusDot } from "@/components/StatusDot";
import { backend, type Bag, type BagFilter } from "@/data/backend";
import { useT } from "@/i18n";
import type { DictStringKey } from "@/i18n/types";
import { toUserFriendly } from "@/lib/address";
import { SC } from "@/lib/colors";
import { EMPTY, ago, formatBytes, shorten } from "@/lib/format";
import { bagGatewayUrl } from "@/lib/gateway";
import { describeStatus, filterColor, reasonText, reasonTone, stateText, stateTone } from "@/lib/status";
import { useCatalog } from "@/stores/catalog";
import { type MouseEvent, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import styles from "./ProviderBags.module.css";

const TITLES: Record<BagFilter, DictStringKey> = {
  all: "bagsAll",
  confirmed: "bagsConfirmed",
  downloading: "bagsDownloading",
  not_paid: "bagsNotPaid",
  unavailable: "bagsUnavailable",
  not_confirmed: "bagsNotConfirmed",
  closed: "bagsClosed",
  not_accepted: "bagsNotAccepted",
  check: "bagsCheck",
};

const PAGE_SIZE = 8;
const SKELETON_FALLBACK = 3;
const SEARCH_DEBOUNCE = 300;

function readState(value: string | null): BagFilter {
  return value != null && value !== "all" && value in TITLES ? (value as BagFilter) : "all";
}

export function ProviderBags() {
  const t = useT();
  const navigate = useNavigate();
  const { pubkey = "" } = useParams();
  const [params] = useSearchParams();
  const location = useLocation();
  const state = readState(params.get("state"));
  const expected = (location.state as { count?: number } | null)?.count;
  const skeletons = Math.min(expected || SKELETON_FALLBACK, PAGE_SIZE);

  const providers = useCatalog((s) => s.providers);
  const load = useCatalog((s) => s.load);
  const provider = providers.find((p) => p.pubkey === pubkey);

  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Bag[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const timer = setTimeout(() => {
      void backend
        .providerBags(pubkey, state, 0, query)
        .then((res) => {
          if (!alive) return;
          setItems(res.items);
          setTotal(res.total);
        })
        .catch(() => {
          if (alive) setFailed(true);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, query ? SEARCH_DEBOUNCE : 0);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [pubkey, state, query]);

  const loadMore = () => {
    void backend
      .providerBags(pubkey, state, items.length, query)
      .then((res) => {
        setItems((prev) => [...prev, ...res.items]);
        setTotal(res.total);
      })
      .catch(() => {});
  };

  const openBag = (bag: Bag) => (event: MouseEvent<HTMLDivElement>) => {
    if ((event.target as Element).closest("a")) return;
    navigate(`/bags?q=${encodeURIComponent(bag.bag_id ?? bag.address)}`);
  };

  const view = provider ? describeStatus(provider, t) : null;
  const color = view?.color ?? SC.gray;
  const nowSec = Math.floor(Date.now() / 1000);
  const header = <ProviderHeader pubkey={pubkey} color={color} onBack={() => navigate(-1)} />;

  return (
    <Screen header={header}>
      <div className={styles.about}>
        <div className={styles.aboutHead}>
          <StatusDot color={filterColor(state)} size={8} />
          {t[TITLES[state]]}
        </div>
        <div className={styles.aboutText}>{t.bagsAbout[state]}</div>
      </div>
      <Field
        glyph="search"
        className={styles.search}
        value={query}
        onChange={setQuery}
        placeholder={t.bagsSearch}
        enterKeyHint="search"
      />
      {loading ? (
        <>
          <div className={styles.count}>
            <span className={styles.countBar} />
          </div>
          <div className={styles.list}>
            {Array.from({ length: skeletons }, (_, i) => (
              <BagCardSkeleton key={i} />
            ))}
          </div>
        </>
      ) : failed ? (
        <Callout glyph="close" title={t.bagsLoadError} iconColor="var(--ts-hint)" />
      ) : total === 0 ? (
        <Callout glyph="search" title={t.bagsNothingFound} iconColor="var(--ts-hint)" />
      ) : (
        <>
          <div className={styles.count}>
            {t[TITLES[state]]} · {total}
          </div>
          <div className={styles.list}>
            {items.map((bag) => (
              <div key={bag.address} className={styles.card} onClick={openBag(bag)}>
                <div className={styles.title} style={{ color: SC[stateTone(bag.state)] }}>
                  {stateText(bag.state, t)}
                </div>
                <div className={styles.sub} style={bag.reason ? { color: SC[reasonTone(bag.reason)] } : undefined}>
                  {reasonText(bag.reason, t)}
                </div>
                {bag.bag_id && (
                  <CopyRow label={t.bagId} copyValue={bag.bag_id} divider compact>
                    <a
                      className={styles.link}
                      href={bagGatewayUrl(bag.bag_id)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {shorten(bag.bag_id, 12).toUpperCase()}
                    </a>
                  </CopyRow>
                )}
                <ExplorerAddressRow label={t.bagContract} address={bag.address} divider compact />
                {bag.owner_address && (
                  <ExplorerAddressRow label={t.bagOwner} address={toUserFriendly(bag.owner_address)} divider compact />
                )}
                <FieldRow
                  label={t.lastProof}
                  value={bag.last_proof_at ? ago(nowSec - bag.last_proof_at, t) : EMPTY}
                  divider
                  compact
                />
                {bag.size != null && <FieldRow label={t.bagSize} value={formatBytes(bag.size)} divider compact />}
              </div>
            ))}
          </div>
          {items.length < total && <LoadMore onClick={loadMore} />}
        </>
      )}
    </Screen>
  );
}

// Rows the card will show once loaded: the first three carry a copy button and so
// stand taller.
const SKELETON_ROWS: { label: string; value: string; copy: boolean }[] = [
  { label: "12%", value: "34%", copy: true },
  { label: "22%", value: "30%", copy: true },
  { label: "24%", value: "40%", copy: true },
  { label: "26%", value: "22%", copy: false },
  { label: "18%", value: "18%", copy: false },
];

function BagCardSkeleton() {
  return (
    <div className={styles.skeleton}>
      <div className={styles.title}>
        <span className={styles.skTitle} />
      </div>
      <div className={styles.sub}>
        <span className={styles.skSub} />
      </div>
      {SKELETON_ROWS.map((row) => (
        <div key={row.label} className={row.copy ? styles.skRowCopy : styles.skRow}>
          <span className={styles.skBar} style={{ width: row.label }} />
          <span className={styles.skBar} style={{ width: row.value }} />
        </div>
      ))}
    </div>
  );
}

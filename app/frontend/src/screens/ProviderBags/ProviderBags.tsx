import { CopyButton } from "@/components/CopyButton";
import { Callout } from "@/components/Callout";
import { LoadMore } from "@/components/LoadMore";
import { ProviderHeader } from "@/components/ProviderHeader";
import { Screen } from "@/components/Screen";
import { StatusDot } from "@/components/StatusDot";
import { backend, type ProblemBag } from "@/data/backend";
import { useT } from "@/i18n";
import type { Dict } from "@/i18n/types";
import { SC } from "@/lib/colors";
import { JUST_NOW_SEC, formatBytes, formatTime, shorten } from "@/lib/format";
import { describeStatus, reasonText, reasonTone } from "@/lib/status";
import { useCatalog } from "@/stores/catalog";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { BagSheet } from "./BagSheet";
import styles from "./ProviderBags.module.css";

function bagAge(secs: number, t: Dict): string {
  return secs < JUST_NOW_SEC ? t.bagCheckedNow : t.bagChecked(formatTime(secs, t, true));
}

export function ProviderBags() {
  const t = useT();
  const navigate = useNavigate();
  const { pubkey = "" } = useParams();

  const providers = useCatalog((s) => s.providers);
  const load = useCatalog((s) => s.load);
  const provider = providers.find((p) => p.pubkey === pubkey);

  const [items, setItems] = useState<ProblemBag[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<ProblemBag | null>(null);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let alive = true;
    void backend
      .bagProblems(pubkey, 0)
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
    return () => {
      alive = false;
    };
  }, [pubkey]);

  const loadMore = () => {
    void backend
      .bagProblems(pubkey, items.length)
      .then((res) => {
        setItems((prev) => [...prev, ...res.items]);
        setTotal(res.total);
      })
      .catch(() => {});
  };

  const view = provider ? describeStatus(provider, t) : null;
  const color = view?.color ?? SC.gray;
  const skeletonCount = 3;
  const nowSec = Math.floor(Date.now() / 1000);

  const header = <ProviderHeader pubkey={pubkey} color={color} onBack={() => navigate(-1)} />;

  return (
    <>
      <Screen header={header}>
        {loading ? (
        <>
          <div className={styles.count}>
            <span className={styles.countBar} />
          </div>
          <div className={styles.list}>
            {Array.from({ length: skeletonCount }, (_, i) => (
              <div key={i} className={styles.skeleton}>
                <div className={styles.main}>
                  <div className={styles.head}>
                    <span className={styles.skBid} />
                  </div>
                  <div className={styles.status}>
                    <span className={styles.skStatus} />
                  </div>
                  <div className={styles.meta}>
                    <span className={styles.skMeta} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : failed ? (
        <Callout glyph="close" title={t.bagsLoadError} iconColor="var(--ts-hint)" />
      ) : total === 0 ? (
        <Callout glyph="check" title={t.bagsFailedEmpty} iconColor={SC.green} />
      ) : (
        <>
          <div className={styles.count}>
            {t.bagsFailedTitle} · {total}
          </div>
          <div className={styles.list}>
            {items.map((bag) => (
              <div key={bag.address} className={styles.row} onClick={() => setSelected(bag)}>
                <div className={styles.main}>
                  <div className={styles.head}>
                    <span className={styles.bid}>{shorten(bag.bag_id, 14).toUpperCase()}</span>
                    <CopyButton value={bag.bag_id} />
                  </div>
                  <div className={styles.status}>
                    <StatusDot color={SC[reasonTone(bag.reason)]} size={7} />
                    <span className={styles.rt}>{reasonText(bag.reason, t)}</span>
                  </div>
                  <div className={styles.meta}>{bagAge(nowSec - bag.reason_at, t)}</div>
                </div>
                {bag.size != null && <span className={styles.rsize}>{formatBytes(bag.size)}</span>}
              </div>
            ))}
          </div>
          {items.length < total && <LoadMore onClick={loadMore} />}
        </>
      )}
      </Screen>
      {selected && <BagSheet bag={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

import { LoadMore } from "@/components/LoadMore";
import { ProviderRow } from "@/components/ProviderRow";
import type { Provider } from "@/data/types";
import type { ReactNode } from "react";
import styles from "./Home.module.css";

const CELL_COUNT = 6;

interface ProviderPaneProps {
  hero?: ReactNode;
  toolbar?: ReactNode;
  count: string | null;
  loading: boolean;
  skeletonCount: number;
  rows: Provider[];
  trailing: (provider: Provider) => ReactNode;
  fallback?: ReactNode;
  onOpen: (pubkey: string) => void;
  onLoadMore?: () => void;
}

export function ProviderPane({
  hero,
  toolbar,
  count,
  loading,
  skeletonCount,
  rows,
  trailing,
  fallback,
  onOpen,
  onLoadMore,
}: ProviderPaneProps) {
  return (
    <>
      {hero}
      {toolbar}
      {(count !== null || loading) && <div className={styles.count}>{count || " "}</div>}

      {loading ? (
        <div className={styles.list}>
          {Array.from({ length: skeletonCount }, (_, index) => (
            <div key={index} className={styles.skeleton}>
              <div className={styles.skHead}>
                <span className={styles.skToggle} />
                <span className={styles.skKey} />
                <span className={styles.skSpacer} />
                <span className={styles.skStatus} />
              </div>
              <div className={styles.skCells}>
                {Array.from({ length: CELL_COUNT }, (_, cell) => (
                  <span key={cell} className={styles.skCell}>
                    <span className={styles.skLabel} />
                    <span className={styles.skValue} />
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : rows.length > 0 ? (
        <div className={styles.list}>
          {rows.map((provider) => (
            <ProviderRow
              key={provider.pubkey}
              provider={provider}
              onOpen={() => onOpen(provider.pubkey)}
              trailing={trailing(provider)}
            />
          ))}
        </div>
      ) : (
        <div className={styles.fallback}>{fallback}</div>
      )}

      {!loading && onLoadMore && <LoadMore onClick={onLoadMore} />}
    </>
  );
}

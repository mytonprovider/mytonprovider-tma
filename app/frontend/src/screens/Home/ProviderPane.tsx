import { LoadMore } from "@/components/LoadMore";
import { ProviderRow, ProviderRowPlaceholder } from "@/components/ProviderRow";
import type { Provider } from "@/data/types";
import type { ReactNode } from "react";
import styles from "./Home.module.css";

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
  expectMore?: boolean;
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
  expectMore,
}: ProviderPaneProps) {
  return (
    <>
      {hero}
      {toolbar}
      {(count !== null || loading) && <div className={styles.count}>{count || " "}</div>}

      {loading ? (
        <div className={styles.list}>
          {Array.from({ length: skeletonCount }, (_, index) => (
            <ProviderRowPlaceholder key={index} />
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

      {loading
        ? expectMore && <span className={styles.moreBar} />
        : onLoadMore && <LoadMore onClick={onLoadMore} />}
    </>
  );
}

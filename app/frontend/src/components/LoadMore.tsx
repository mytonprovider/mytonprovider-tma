import { useT } from "@/i18n";
import styles from "./LoadMore.module.css";

export function LoadMore({ onClick }: { onClick: () => void }) {
  const t = useT();
  return (
    <button type="button" className={styles.button} onClick={onClick}>
      {t.loadMore}
    </button>
  );
}

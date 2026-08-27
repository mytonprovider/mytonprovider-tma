import { BottomSheet } from "@/components/BottomSheet";
import { useT } from "@/i18n";
import { cx } from "@/lib/cx";
import styles from "./ConfirmSheet.module.css";

interface ConfirmSheetProps {
  title: string;
  subtitle?: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmSheet({ title, subtitle, confirmLabel, onConfirm, onClose }: ConfirmSheetProps) {
  const t = useT();
  return (
    <BottomSheet title={title} subtitle={subtitle} onClose={onClose}>
      {(close) => (
        <div className={styles.actions}>
          <button type="button" className={cx(styles.btn, styles.ghost)} onClick={close}>
            {t.cancel}
          </button>
          <button
            type="button"
            className={cx(styles.btn, styles.danger)}
            onClick={() => {
              onConfirm();
              close();
            }}
          >
            {confirmLabel}
          </button>
        </div>
      )}
    </BottomSheet>
  );
}

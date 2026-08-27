import { BottomSheet } from "@/components/BottomSheet";
import { Card } from "@/components/Card";
import { CopyRow } from "@/components/CopyRow";
import { ExplorerAddressRow } from "@/components/ExplorerAddressRow";
import { FieldRow } from "@/components/FieldRow";
import type { ProblemBag } from "@/data/backend";
import { useT } from "@/i18n";
import { toUserFriendly } from "@/lib/address";
import { SC } from "@/lib/colors";
import { ago, formatBytes, shorten } from "@/lib/format";
import { bagGatewayUrl } from "@/lib/gateway";
import { reasonText, reasonTone } from "@/lib/status";
import { useNavigate } from "react-router-dom";
import styles from "./BagSheet.module.css";

interface BagSheetProps {
  bag: ProblemBag;
  onClose: () => void;
}

export function BagSheet({ bag, onClose }: BagSheetProps) {
  const t = useT();
  const navigate = useNavigate();
  const nowSec = Math.floor(Date.now() / 1000);

  return (
    <BottomSheet onClose={onClose}>
      {(close) => (
        <>
          <div className={styles.head} style={{ color: SC[reasonTone(bag.reason)] }}>
            {reasonText(bag.reason, t)}
          </div>
          <Card>
            <CopyRow label={t.bagId} copyValue={bag.bag_id}>
              <a className={styles.link} href={bagGatewayUrl(bag.bag_id)} target="_blank" rel="noopener noreferrer">
                {shorten(bag.bag_id, 12).toUpperCase()}
              </a>
            </CopyRow>
            <ExplorerAddressRow label={t.bagContract} address={bag.address} divider />
            {bag.owner_address && <ExplorerAddressRow label={t.bagOwner} address={toUserFriendly(bag.owner_address)} divider />}
            {bag.size != null && <FieldRow label={t.bagSize} value={formatBytes(bag.size)} divider />}
            <FieldRow label={t.bagCheckedLabel} value={ago(nowSec - bag.reason_at, t)} divider />
            <FieldRow label={t.bagReason} value={bag.reason} divider />
          </Card>
          <button
            className={styles.openBtn}
            type="button"
            onClick={() => {
              close();
              navigate(`/bags?q=${bag.bag_id}`);
            }}
          >
            {t.bagOpen}
          </button>
        </>
      )}
    </BottomSheet>
  );
}

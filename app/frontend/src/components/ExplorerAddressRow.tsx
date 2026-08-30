import { CopyRow } from "@/components/CopyRow";
import { TrustedBadge } from "@/components/TrustedBadge";
import { explorerAddressUrl } from "@/lib/address";
import { shorten } from "@/lib/format";
import { useNames } from "@/stores/names";
import { useSettings } from "@/stores/settings";
import styles from "./ExplorerAddressRow.module.css";

interface ExplorerAddressRowProps {
  label: string;
  address: string;
  divider?: boolean;
  compact?: boolean;
}

export function ExplorerAddressRow({ label, address, divider, compact }: ExplorerAddressRowProps) {
  const explorer = useSettings((s) => s.explorer);
  const name = useNames((s) => s.addresses[address]);
  const nameClass = compact ? styles.nameCompact : styles.name;
  const linkClass = compact ? styles.linkCompact : styles.link;
  return (
    <CopyRow label={label} copyValue={address} divider={divider} compact={compact}>
      <a
        className={name ? nameClass : linkClass}
        href={explorerAddressUrl(address, explorer)}
        target="_blank"
        rel="noopener noreferrer"
      >
        {name || shorten(address, 12)}
      </a>
      <TrustedBadge address={address} />
    </CopyRow>
  );
}

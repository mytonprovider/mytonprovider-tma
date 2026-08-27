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
}

export function ExplorerAddressRow({ label, address, divider }: ExplorerAddressRowProps) {
  const explorer = useSettings((s) => s.explorer);
  const name = useNames((s) => s.addresses[address]);
  return (
    <CopyRow label={label} copyValue={address} divider={divider}>
      <a
        className={name ? styles.name : styles.link}
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

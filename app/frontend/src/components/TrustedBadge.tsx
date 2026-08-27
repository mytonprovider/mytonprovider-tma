import { toUserFriendly } from "@/lib/address";
import { useTrusted } from "@/stores/trusted";
import styles from "./TrustedBadge.module.css";

export const BADGE_SRC = "/badge-verified.webp";

export function TrustedBadge({ address }: { address: string }) {
  const trusted = useTrusted((s) => s.addresses.includes(toUserFriendly(address)));
  if (!trusted) return null;
  return <img className={styles.badge} src={BADGE_SRC} alt="" />;
}

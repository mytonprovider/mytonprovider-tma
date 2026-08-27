import { CopyButton } from "@/components/CopyButton";
import { Icon } from "@/components/Icon/Icon";
import { ScreenHeader } from "@/components/ScreenHeader";
import { StatusDot } from "@/components/StatusDot";
import { toggleBell, toggleFavorite } from "@/data/sync";
import { useT } from "@/i18n";
import { ACCENT } from "@/lib/colors";
import { shorten } from "@/lib/format";
import { useFavorites } from "@/stores/favorites";
import { useNames } from "@/stores/names";
import { useSubscriptions } from "@/stores/subscriptions";
import styles from "./ProviderHeader.module.css";

interface ProviderHeaderProps {
  pubkey: string;
  color: string;
  onBack: () => void;
}

export function ProviderHeader({ pubkey, color, onBack }: ProviderHeaderProps) {
  const t = useT();
  const isFavorite = useFavorites((s) => s.favorites.includes(pubkey));
  const isSubscribed = useSubscriptions((s) => s.subscribed.includes(pubkey));
  const isAlertOff = useSubscriptions((s) => s.alertsOff.includes(pubkey));
  const name = useNames((s) => s.providers[pubkey]);

  return (
    <ScreenHeader
      title={
        <span className={styles.navTitle}>
          <StatusDot color={color} size={8} />
          <span className={styles.navName}>{name || shorten(pubkey, 14).toUpperCase()}</span>
          <CopyButton value={pubkey} />
        </span>
      }
      onBack={onBack}
      right={
        <div className={styles.headerActions}>
          {isSubscribed ? (
            <button type="button" aria-label={t.notifBtn} className={styles.headerBtn} onClick={() => toggleBell(pubkey)}>
              <Icon glyph="bell" size={22} fill={isAlertOff ? "none" : ACCENT} strokeColor={isAlertOff ? "var(--ts-hint)" : ACCENT} />
            </button>
          ) : (
            <button type="button" aria-label={t.fav} className={styles.headerBtn} onClick={() => toggleFavorite(pubkey)}>
              <Icon glyph="star" size={22} fill={isFavorite ? ACCENT : "none"} strokeColor={isFavorite ? ACCENT : "var(--ts-hint)"} />
            </button>
          )}
        </div>
      }
    />
  );
}

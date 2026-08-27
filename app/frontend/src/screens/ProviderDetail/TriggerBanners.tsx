import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import { ownerTriggers } from "@/data/owner";
import { useOwnerData } from "@/hooks/useOwnerData";
import { useT } from "@/i18n";
import type { TriggerKey } from "@/i18n/types";
import { SC, tint } from "@/lib/colors";
import { useAuth } from "@/stores/auth";
import { useSubscriptions } from "@/stores/subscriptions";
import styles from "./ProviderDetail.module.css";

const TRIGGER_GLYPH: Record<TriggerKey, GlyphName> = {
  telemetry_lost: "bars",
  not_online: "server",
  cpu_high: "cpu",
  ram_high: "bars",
  network_high: "globe",
  disk_load_high: "bars",
  disk_space_low: "server",
};

export function TriggerBanners({ pubkey }: { pubkey: string }) {
  const t = useT();
  const loggedIn = useAuth((s) => s.loggedIn);
  const isSubscribed = useSubscriptions((s) => s.subscribed.includes(pubkey));
  const { payload } = useOwnerData(pubkey, isSubscribed && loggedIn, "today");
  const triggers = payload ? ownerTriggers(payload.triggers) : [];

  return (
    <>
      {triggers.map((trigger) => {
        const color = trigger.color === "red" ? SC.red : SC.orange;
        return (
          <div key={trigger.key} className={styles.triggerBanner} style={{ background: tint(color, 0.12) }}>
            <Icon glyph={TRIGGER_GLYPH[trigger.key]} size={16} color={color} />
            <span className={styles.bannerText} style={{ color }}>
              {t.triggerNames[trigger.key]}
            </span>
          </div>
        );
      })}
    </>
  );
}

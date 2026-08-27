import { CopyButton } from "@/components/CopyButton";
import { StatusDot } from "@/components/StatusDot";
import type { Provider } from "@/data/types";
import { useT } from "@/i18n";
import { SC, rankColor, tint } from "@/lib/colors";
import { EMPTY, KEY_CHARS, amount, fitKey, formatPrice, formatSpace, formatTime, freeSpaceTone, spaceFreePercent, trimDown } from "@/lib/format";
import { describeStatus } from "@/lib/status";
import { useCatalog } from "@/stores/catalog";
import { useNames } from "@/stores/names";
import { useKeyChars } from "@/hooks/useKeyChars";
import { type ReactNode, useRef } from "react";
import styles from "./ProviderRow.module.css";

interface ProviderRowProps {
  provider: Provider;
  onOpen: () => void;
  trailing: ReactNode;
}

function withUnits(text: string): ReactNode {
  return text.split(/([\d.,]+)/).map((part, index) =>
    !part || /^[\d.,]/.test(part) ? (
      part
    ) : (
      <span key={index} className={styles.unit}>
        {part}
      </span>
    ),
  );
}

function freeSpace(provider: Provider): string {
  const { totalSpaceBytes, usedSpaceBytes } = provider.telemetry;
  if (!provider.hasTelemetry || totalSpaceBytes === null || usedSpaceBytes === null) return EMPTY;
  return formatSpace(Math.max(totalSpaceBytes - usedSpaceBytes, 0));
}

export function ProviderRow({ provider, onOpen, trailing }: ProviderRowProps) {
  const t = useT();
  const headRef = useRef<HTMLDivElement>(null);
  const pkRef = useRef<HTMLSpanElement>(null);
  const keyChars = useKeyChars(headRef, pkRef, KEY_CHARS);
  const status = describeStatus(provider, t);
  const rank = useCatalog((s) => s.ranks[provider.pubkey]);
  const name = useNames((s) => s.providers[provider.pubkey]);
  const freePercent = provider.hasTelemetry
    ? spaceFreePercent(provider.telemetry.totalSpaceBytes, provider.telemetry.usedSpaceBytes)
    : null;
  const place = provider.location?.country || provider.location?.countryIso || EMPTY;
  const working = provider.workingTime > 0 ? formatTime(provider.workingTime, t, true) : EMPTY;

  const cell = (label: ReactNode, value: ReactNode) => (
    <span className={styles.cell}>
      <span className={styles.cellLabel}>{label}</span>
      <span className={styles.cellValue}>{value}</span>
    </span>
  );

  return (
    <div className={styles.row} onClick={onOpen}>
      <div ref={headRef} className={styles.head}>
        {trailing}
        {name ? (
          <span className={styles.name}>{name}</span>
        ) : (
          <span ref={pkRef} className={styles.pk}>
            {fitKey(provider.pubkey, keyChars).toUpperCase()}
          </span>
        )}
        <CopyButton value={provider.pubkey} />
        <span
          className={styles.status}
          style={{
            color: status.color,
            background: tint(status.color, 0.14),
            boxShadow: `inset 0 0 0 1px ${tint(status.color, 0.32)}`,
          }}
        >
          <StatusDot color={status.color} size={7} />
          {status.label}
          {status.hasRatio && <span className={styles.ratio}>{trimDown(status.ratio * 100, 0)}%</span>}
        </span>
      </div>
      <div className={styles.cells}>
        {cell(
          rank ? (
            <>
              {t.rating} <b className={styles.mark} style={{ color: rankColor(rank) }}>{`#${rank}`}</b>
            </>
          ) : (
            t.rating
          ),
          amount(provider.rating),
        )}
        {cell(t.uptime, `${amount(provider.uptime)}%`)}
        {cell(t.price, withUnits(`${formatPrice(provider.price)} GRAM`))}
        {cell(
          freePercent === null ? (
            t.freeLabel
          ) : (
            <>
              {t.freeLabel}{" "}
              <b className={styles.mark} style={{ color: SC[freeSpaceTone(freePercent)] }}>
                {`${Math.round(freePercent)}%`}
              </b>
            </>
          ),
          withUnits(freeSpace(provider)),
        )}
        {cell(t.workingTime, withUnits(working))}
        {cell(t.location, place)}
      </div>
    </div>
  );
}

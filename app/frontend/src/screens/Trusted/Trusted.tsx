import { Card } from "@/components/Card";
import { Callout } from "@/components/Callout";
import { Field } from "@/components/Field";
import { Icon } from "@/components/Icon/Icon";
import { NameSheet } from "@/components/NameSheet";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { BADGE_SRC } from "@/components/TrustedBadge";
import { toggleTrusted } from "@/data/sync";
import { useT } from "@/i18n";
import { explorerAddressUrl, parseAddress } from "@/lib/address";
import { cx } from "@/lib/cx";
import { shorten } from "@/lib/format";
import { useSettings } from "@/stores/settings";
import { useNames } from "@/stores/names";
import { useTrusted } from "@/stores/trusted";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Trusted.module.css";

type Invalid = "none" | "format" | "duplicate";

export function Trusted() {
  const t = useT();
  const navigate = useNavigate();
  const explorer = useSettings((s) => s.explorer);
  const addresses = useTrusted((s) => s.addresses);
  const names = useNames((s) => s.addresses);

  const [value, setValue] = useState("");
  const [invalid, setInvalid] = useState<Invalid>("none");
  const [editing, setEditing] = useState<string | null>(null);

  const submit = () => {
    const address = parseAddress(value.trim());
    if (address === null) {
      setInvalid("format");
      return;
    }
    if (addresses.includes(address)) {
      setInvalid("duplicate");
      return;
    }
    toggleTrusted(address);
    setValue("");
  };

  const header = <ScreenHeader title={t.trustedTitle} onBack={() => navigate(-1)} />;

  return (
    <Screen header={header}>
      <Field
        className={styles.field}
        value={value}
        onChange={(next) => {
          setValue(next);
          setInvalid("none");
        }}
        placeholder={t.trustedPlaceholder}
        enterKeyHint="done"
        invalid={invalid !== "none"}
        onEnter={submit}
        trailing={
          <button type="button" className={styles.add} disabled={!value.trim()} onClick={submit}>
            {t.trustedAdd}
          </button>
        }
      />
      <div className={styles.error}>
        {invalid === "format" ? t.trustedInvalid : invalid === "duplicate" ? t.trustedDuplicate : ""}
      </div>

      {addresses.length === 0 ? (
        <Callout glyph="check" title={t.trustedEmptyTitle} desc={t.trustedEmptyDesc} />
      ) : (
        <>
          <div className={styles.count}>{t.trustedCount(addresses.length)}</div>
          <Card>
            {addresses.map((address, index) => (
              <div key={address} className={cx(styles.row, index > 0 && styles.divider)}>
                <a
                  className={names[address] ? styles.name : styles.link}
                  href={explorerAddressUrl(address, explorer)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {names[address] || shorten(address, 14)}
                </a>
                <span className={styles.actions}>
                  <button
                    type="button"
                    aria-label={t.nameEdit}
                    className={styles.action}
                    onClick={() => setEditing(address)}
                  >
                    <Icon glyph="edit" size={16} color="var(--ts-hint)" />
                  </button>
                  <button
                    type="button"
                    aria-label={t.trustedRemove}
                    className={styles.action}
                    onClick={() => toggleTrusted(address)}
                  >
                    <Icon glyph="close" size={16} color="var(--ts-danger)" stroke={2} />
                  </button>
                </span>
              </div>
            ))}
          </Card>
          <div className={styles.note}>
            {t.trustedNote}
            <img className={styles.noteBadge} src={BADGE_SRC} alt="" />
          </div>
        </>
      )}
      {editing !== null && (
        <NameSheet
          kind="address"
          target={editing}
          subtitle={shorten(editing, 14)}
          onClose={() => setEditing(null)}
        />
      )}
    </Screen>
  );
}

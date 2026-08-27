import { endSession } from "@/app/session";
import { Icon } from "@/components/Icon/Icon";
import type { GlyphName } from "@/components/Icon/glyphs";
import { SegmentControl } from "@/components/SegmentControl";
import { TelegramLoginButton } from "@/components/TelegramLoginButton";
import { backend } from "@/data/backend";
import { setExplorer, setLanguage, setTheme } from "@/data/sync";
import { useAppliedTheme } from "@/hooks/useTheme";
import { useAppliedLang, useT } from "@/i18n";
import type { Lang } from "@/i18n/types";
import { isInTelegram, notify } from "@/lib/telegram";
import { useAuth } from "@/stores/auth";
import { type Explorer, type Theme, useSettings } from "@/stores/settings";
import { useTrusted } from "@/stores/trusted";
import { useNavigate } from "react-router-dom";
import styles from "./MenuSheet.module.css";

interface MenuRowProps {
  glyph: GlyphName;
  label: string;
  count?: number;
  href?: string;
  external?: boolean;
  onClick?: () => void;
}

function MenuRow({ glyph, label, count, href, external, onClick }: MenuRowProps) {
  const body = (
    <>
      <span className={styles.tile}>
        <Icon glyph={glyph} size={17} color="var(--ts-on-accent)" />
      </span>
      {label}
      <span className={styles.tail}>
        {count ? <span className={styles.count}>{count}</span> : null}
        <Icon glyph={external ? "external" : "chevron"} size={external ? 15 : 16} color="var(--ts-hint)" />
      </span>
    </>
  );

  if (!href) {
    return (
      <button type="button" className={styles.row} onClick={onClick}>
        {body}
      </button>
    );
  }

  return (
    <a className={styles.row} href={href} {...(external && { target: "_blank", rel: "noopener noreferrer" })}>
      {body}
    </a>
  );
}

export function MenuSheet() {
  const t = useT();
  const navigate = useNavigate();

  const theme = useAppliedTheme();
  const lang = useAppliedLang();
  const explorer = useSettings((s) => s.explorer);

  const trustedCount = useTrusted((s) => s.addresses.length);

  const loggedIn = useAuth((s) => s.loggedIn);
  const user = useAuth((s) => s.user);
  const isAdmin = useAuth((s) => s.isAdmin);
  const inTelegram = isInTelegram();

  const openAdmin = () => {
    void backend
      .adminSession()
      .then(() => location.assign(`/admin/#theme=${theme}`))
      .catch(() => notify("error"));
  };

  return (
    <>
      <div className={styles.accountSlot}>
        {loggedIn && user ? (
          <div className={styles.account}>
            {user.photoUrl ? (
              <img className={styles.avatar} src={user.photoUrl} alt="" />
            ) : (
              <div className={styles.avatar}>{user.initials}</div>
            )}
            <div className={styles.accountInfo}>
              <div className={styles.accountName}>{user.name}</div>
              {user.username && <div className={styles.accountUser}>@{user.username}</div>}
            </div>
            {!inTelegram && (
              <button
                type="button"
                aria-label={t.logout}
                className={styles.logout}
                onClick={endSession}
              >
                <Icon glyph="logout" size={20} color="var(--ts-danger)" />
              </button>
            )}
          </div>
        ) : (
          !inTelegram && (
            <div className={styles.login}>
              <TelegramLoginButton />
            </div>
          )
        )}
      </div>

      <div className={styles.separator} />

      <div className={styles.label}>{t.language}</div>
      <SegmentControl<Lang>
        options={[
          { value: "en", label: "English" },
          { value: "ru", label: "Русский" },
        ]}
        value={lang}
        onChange={setLanguage}
      />

      <div className={styles.label}>{t.appearance}</div>
      <SegmentControl<Theme>
        options={[
          { value: "light", label: t.light },
          { value: "dark", label: t.dark },
        ]}
        value={theme}
        onChange={setTheme}
      />

      <div className={styles.label}>{t.explorerLabel}</div>
      <SegmentControl<Explorer>
        options={[
          { value: "tonviewer", label: "Tonviewer" },
          { value: "tonscan", label: "Tonscan" },
        ]}
        value={explorer}
        onChange={setExplorer}
      />

      <div className={styles.group}>
        {isAdmin && <MenuRow glyph="sliders" label={t.adminPanel} onClick={openAdmin} />}
        <MenuRow glyph="search" label={t.explorerTitle} onClick={() => navigate("/bags")} />
        <MenuRow glyph="check" label={t.trustedTitle} count={trustedCount} onClick={() => navigate("/trusted")} />
        <MenuRow glyph="server" label={t.becomeProvider} href="https://github.com/igroman787/mytonprovider" external />
        <MenuRow glyph="telegram" label={t.support} href="https://t.me/mytonprovider_chat" external />
      </div>
    </>
  );
}

import { useT } from "@/i18n";
import { isInTelegram } from "@/lib/telegram";
import { useEffect, useState } from "react";
import styles from "./InstallBanner.module.css";

const DISMISS_KEY = "mtp-install-dismissed";

function isStandalone(): boolean {
  const nav = navigator as Navigator & { standalone?: boolean };
  return window.matchMedia("(display-mode: standalone)").matches || nav.standalone === true;
}

function isIOSSafari(): boolean {
  const ua = navigator.userAgent;
  const iOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const otherBrowser = /crios|fxios|edgios|opios|android/i.test(ua);
  return iOS && !otherBrowser;
}

function ShareGlyph() {
  return (
    <svg className={styles.share} viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
      <path
        d="M12 3v11M12 3l-3.2 3.2M12 3l3.2 3.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M7 10H6a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-1"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function InstallBanner() {
  const t = useT();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isInTelegram() || isStandalone() || localStorage.getItem(DISMISS_KEY)) return;
    if (isIOSSafari()) setVisible(true);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  return (
    <div className={styles.banner}>
      <div className={styles.body}>
        <div className={styles.title}>{t.installTitle}</div>
        <div className={styles.hint}>
          {t.installStep1}
          <ShareGlyph />
          {t.installStep2}
        </div>
      </div>
      <button className={styles.close} onClick={dismiss} aria-label={t.installHide}>
        ×
      </button>
    </div>
  );
}

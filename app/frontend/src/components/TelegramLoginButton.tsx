import { Icon } from "@/components/Icon/Icon";
import { useLogin } from "@/hooks/useLogin";
import { useT } from "@/i18n";
import styles from "./TelegramLoginButton.module.css";

export function TelegramLoginButton() {
  const t = useT();
  const { start } = useLogin();
  return (
    <button type="button" className={styles.button} onClick={start}>
      <Icon glyph="telegram" size={20} color="#fff" />
      {t.loginTg}
    </button>
  );
}

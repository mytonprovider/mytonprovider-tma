import { BottomBar } from "@/components/BottomBar";
import { Card } from "@/components/Card";
import { MainButton } from "@/components/MainButton";
import { Screen } from "@/components/Screen";
import { ScreenHeader } from "@/components/ScreenHeader";
import { SectionHeader } from "@/components/SectionHeader";
import { ThresholdSlider } from "@/components/ThresholdSlider";
import { Toggle } from "@/components/Toggle";
import { ALERT_TYPES, DEFAULT_THRESHOLD } from "@/data/alerts";
import { saveAlerts, setAlertThreshold, setAlertsEnabled, toggleAlertType } from "@/data/sync";
import { useT } from "@/i18n";
import { cx } from "@/lib/cx";
import { useAlerts } from "@/stores/alerts";
import { useNavigate } from "react-router-dom";
import styles from "./Alerts.module.css";

export function Alerts() {
  const t = useT();
  const navigate = useNavigate();

  const enabled = useAlerts((s) => s.enabled);
  const types = useAlerts((s) => s.types);
  const thresholds = useAlerts((s) => s.thresholds);

  const onSave = () => {
    saveAlerts();
    navigate(-1);
  };

  return (
    <Screen
      header={<ScreenHeader title={t.alertTitle} onBack={() => navigate(-1)} />}
      bottom={
        <BottomBar>
          <MainButton label={t.save} onClick={onSave} />
        </BottomBar>
      }
    >
      <div className={styles.masterCard}>
        <div className={styles.masterMain}>
          <div className={styles.masterLabel}>{t.alertMasterLabel}</div>
          <div className={styles.masterSub}>{t.alertMasterSub}</div>
        </div>
        <Toggle checked={enabled} onChange={setAlertsEnabled} ariaLabel={t.alertMasterLabel} />
      </div>

      <div className={cx(styles.typesWrap, !enabled && styles.typesWrapOff)}>
        <SectionHeader title={t.alertTypesTitle} />
        <Card>
          {ALERT_TYPES.map((type, index) => {
            const on = types[type.key];
            return (
              <div key={type.key} className={cx(styles.typeRow, index > 0 && styles.typeRowDivider)}>
                <div className={styles.typeToggleRow}>
                  <div className={styles.typeMain}>
                    <div className={styles.typeLabel}>{t.alertNames[type.key]}</div>
                    <div className={styles.typeDesc}>{t.alertDescs[type.key]}</div>
                  </div>
                  <Toggle checked={on} onChange={() => toggleAlertType(type.key)} ariaLabel={t.alertNames[type.key]} />
                </div>
                {type.threshold && (
                  <div className={cx(styles.sliderWrap, !on && styles.sliderWrapOff)}>
                    <ThresholdSlider
                      value={thresholds[type.key] ?? DEFAULT_THRESHOLD}
                      onChange={(value) => setAlertThreshold(type.key, value)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </Card>
      </div>
    </Screen>
  );
}

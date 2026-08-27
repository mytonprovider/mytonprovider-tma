import { BottomSheet } from "@/components/BottomSheet";
import { Field } from "@/components/Field";
import { Icon } from "@/components/Icon/Icon";
import { MainButton } from "@/components/MainButton";
import { BackendError } from "@/data/backend";
import { subscribeWithPassword } from "@/data/sync";
import { useT } from "@/i18n";
import { cx } from "@/lib/cx";
import { notify } from "@/lib/telegram";
import { useEffect, useRef, useState } from "react";
import styles from "./PasswordSheet.module.css";

type PwStatus = "idle" | "checking" | "success";
type PwError = "none" | "wrong" | "locked" | "nopass" | "failed";

const MAX_ATTEMPTS = 3;
const LOCK_MS = 15000;
const SUCCESS_MS = 800;
const SHAKE_MS = 400;

interface PasswordSheetProps {
  pubkey: string;
  onClose: () => void;
}

export function PasswordSheet({ pubkey, onClose }: PasswordSheetProps) {
  const t = useT();
  const [value, setValue] = useState("");
  const [show, setShow] = useState(false);
  const [status, setStatus] = useState<PwStatus>("idle");
  const [error, setError] = useState<PwError>("none");
  const [locked, setLocked] = useState(false);
  const [shaking, setShaking] = useState(false);
  const attempts = useRef(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach(clearTimeout);
  }, []);

  const track = (timer: ReturnType<typeof setTimeout>) => {
    timers.current.push(timer);
  };

  const fail = (next: PwError) => {
    setStatus("idle");
    setError(next);
    setShaking(true);
    notify("error");
    track(setTimeout(() => setShaking(false), SHAKE_MS));
  };

  const lockFor = (ms: number) => {
    setLocked(true);
    fail("locked");
    track(
      setTimeout(() => {
        attempts.current = 0;
        setLocked(false);
        setError("none");
      }, ms),
    );
  };

  const submit = (close: () => void) => {
    if (locked || status === "checking") return;
    const password = value.trim();
    if (!password) {
      fail("wrong");
      return;
    }
    setStatus("checking");
    setError("none");
    subscribeWithPassword(pubkey, password)
      .then(() => {
        setStatus("success");
        notify("success");
        track(setTimeout(close, SUCCESS_MS));
      })
      .catch((error: unknown) => {
        if (error instanceof BackendError && error.detail === "Wrong password") {
          attempts.current += 1;
          if (attempts.current >= MAX_ATTEMPTS) lockFor(LOCK_MS);
          else fail("wrong");
          return;
        }
        if (error instanceof BackendError && error.status === 429) {
          lockFor(LOCK_MS * 4);
          return;
        }
        if (error instanceof BackendError && error.status === 400) {
          fail("nopass");
          return;
        }
        console.error("subscribe failed", error);
        fail("failed");
      });
  };

  const mainState = status === "checking" ? "loading" : status === "success" ? "success" : "idle";
  const errorText =
    error === "locked"
      ? t.pwTooMany
      : error === "wrong"
        ? t.pwWrong
        : error === "nopass"
          ? t.pwNoPass
          : error === "failed"
            ? t.pwFailed
            : "";
  const label = locked ? t.pwLocked : t.pwUnlock;

  return (
    <BottomSheet title={t.pwTitle} subtitle={t.pwSubtitle} onClose={onClose}>
      {(close) => (
        <>
          <Field
            className={cx(styles.field, shaking && styles.fieldShake)}
            glyph="lock"
            invalid={error !== "none"}
            password={!show}
            value={value}
            onChange={(next) => {
              setValue(next);
              setStatus("idle");
              setError("none");
            }}
            placeholder={t.pwPlaceholder}
            trailing={
              <button
                type="button"
                aria-label="Toggle visibility"
                className={styles.eye}
                onClick={() => setShow((prev) => !prev)}
              >
                <Icon glyph="eye" size={18} color="var(--ts-hint)" />
              </button>
            }
          />
          <div className={styles.error}>{errorText}</div>
          <div className={styles.submit}>
            <MainButton label={label} state={mainState} disabled={locked} onClick={() => submit(close)} />
          </div>
        </>
      )}
    </BottomSheet>
  );
}

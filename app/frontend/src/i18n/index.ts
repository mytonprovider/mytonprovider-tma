import { getTelegramUser, isInTelegram } from "@/lib/telegram";
import { useSettings } from "@/stores/settings";
import { useEffect, useState } from "react";
import { en } from "./en";
import { ru } from "./ru";
import type { Dict, Lang } from "./types";

const DICTS: Record<Lang, Dict> = { en, ru };

export function normalizeLang(code: string): Lang {
  return code.toLowerCase().startsWith("ru") ? "ru" : "en";
}

function detectLang(): Lang {
  const telegramCode = isInTelegram() ? getTelegramUser()?.language_code : null;
  return normalizeLang(telegramCode || navigator.language || "");
}

export function useAppliedLang(): Lang {
  const lang = useSettings((state) => state.lang);
  const langAuto = useSettings((state) => state.langAuto);
  const [detected, setDetected] = useState(detectLang);

  useEffect(() => {
    const handler = () => setDetected(detectLang());
    window.addEventListener("languagechange", handler);
    return () => window.removeEventListener("languagechange", handler);
  }, []);

  return langAuto ? detected : lang;
}

export function useT(): Dict {
  return DICTS[useAppliedLang()];
}

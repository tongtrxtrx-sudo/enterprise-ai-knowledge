import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";

import { en } from "./locales/en";
import { zhCN } from "./locales/zh-CN";

const LOCALE_STORAGE_KEY = "kb.locale";

export type Locale = "zh-CN" | "en";
type TranslationDict = Record<string, string>;

const resources: Record<Locale, TranslationDict> = {
    "zh-CN": zhCN,
    en,
};

type I18nContextValue = {
    locale: Locale;
    setLocale: (next: Locale) => void;
    t: (key: string, params?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function isSupportedLocale(value: string | null): value is Locale {
    return value === "zh-CN" || value === "en";
}

function getInitialLocale(): Locale {
    if (typeof window === "undefined") {
        return "zh-CN";
    }
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isSupportedLocale(stored)) {
        return stored;
    }
    return "zh-CN";
}

function formatMessage(template: string, params?: Record<string, string | number>) {
    if (!params) {
        return template;
    }
    return Object.entries(params).reduce((acc, [key, value]) => {
        return acc.replaceAll(`{${key}}`, String(value));
    }, template);
}

export function I18nProvider({ children }: PropsWithChildren) {
    const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

    const value = useMemo<I18nContextValue>(() => {
        return {
            locale,
            setLocale: (next) => {
                setLocaleState(next);
                if (typeof window !== "undefined") {
                    window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
                }
            },
            t: (key, params) => {
                const template = resources[locale][key] ?? resources.en[key] ?? key;
                return formatMessage(template, params);
            },
        };
    }, [locale]);

    return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error("useI18n must be used within I18nProvider");
    }
    return context;
}

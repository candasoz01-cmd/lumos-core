import tr from "./messages/tr";
import en from "./messages/en";

export type Locale = "tr" | "en";
export const LOCALES: Locale[] = ["tr", "en"];
export const DEFAULT_LOCALE: Locale = "en";
const STORAGE_KEY = "lumos_locale";

const catalogs: Record<Locale, typeof tr> = { tr, en };

function getNested(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function getLocale(): Locale {
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "tr" || stored === "en") return stored;
  }
  if (typeof document !== "undefined") {
    const htmlLang = document.documentElement.lang;
    if (htmlLang === "en") return "en";
  }
  return DEFAULT_LOCALE;
}

export function setLocale(locale: Locale): void {
  if (typeof document === "undefined") return;
  localStorage.setItem(STORAGE_KEY, locale);
  document.documentElement.lang = locale;
  document.documentElement.setAttribute("data-locale", locale);
  applyDocumentI18n();
  applyOgLocale(locale);
  window.dispatchEvent(new CustomEvent("lumos:localechange", { detail: { locale } }));
}

function applyOgLocale(locale: Locale): void {
  const ogLocale = document.querySelector('meta[property="og:locale"]');
  if (ogLocale) ogLocale.setAttribute("content", locale === "en" ? "en_US" : "tr_TR");
}

export function t(key: string, locale?: Locale): string {
  const loc = locale ?? getLocale();
  const val = getNested(catalogs[loc] as unknown as Record<string, unknown>, key);
  if (typeof val === "string") return val;
  const fallback = getNested(catalogs.tr as unknown as Record<string, unknown>, key);
  if (typeof fallback === "string") return fallback;
  return key;
}

export function applyDocumentI18n(root: ParentNode = document): void {
  const locale = getLocale();

  root.querySelectorAll<HTMLElement>("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    const val = t(key, locale);
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      if (!el.hasAttribute("data-i18n-placeholder")) el.value = val;
    } else {
      el.textContent = val;
    }
  });

  root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key) el.placeholder = t(key, locale);
  });

  root.querySelectorAll<HTMLElement>("[data-i18n-aria-label]").forEach((el) => {
    const key = el.getAttribute("data-i18n-aria-label");
    if (key) el.setAttribute("aria-label", t(key, locale));
  });

  root.querySelectorAll<HTMLElement>("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (key) {
      el.setAttribute("title", t(key, locale));
      if (el.hasAttribute("aria-label") && el.getAttribute("data-i18n-aria-label") === key) {
        el.setAttribute("aria-label", t(key, locale));
      }
    }
  });

  root.querySelectorAll<HTMLMetaElement>("[data-i18n-content]").forEach((el) => {
    const key = el.getAttribute("data-i18n-content");
    if (key) el.setAttribute("content", t(key, locale));
  });

  root.querySelectorAll<HTMLImageElement>("[data-i18n-src]").forEach((el) => {
    const key = el.getAttribute("data-i18n-src");
    if (key) el.src = t(key, locale);
  });

  /** Phase 2: swap `landing.assets.worldMapDecor` when EN/TR map art diverges. */
  const mapDecor = t("landing.assets.worldMapDecor", locale);
  if (typeof document !== "undefined") {
    const safe = mapDecor.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    document.documentElement.style.setProperty("--lumos-world-map-decor", `url("${safe}")`);
  }

  root.querySelectorAll<HTMLButtonElement>("[data-set-locale]").forEach((btn) => {
    const loc = btn.getAttribute("data-set-locale");
    if (loc !== "tr" && loc !== "en") return;
    const active = loc === locale;
    btn.setAttribute("aria-pressed", active ? "true" : "false");
    btn.classList.toggle("lumos-lang-btn--active", active);
  });
}

export function initI18n(): void {
  const locale = getLocale();
  document.documentElement.lang = locale;
  document.documentElement.setAttribute("data-locale", locale);
  applyDocumentI18n();
  applyOgLocale(locale);

  document.addEventListener("click", (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    const btn = target.closest<HTMLButtonElement>("[data-set-locale]");
    if (!btn) return;
    const loc = btn.getAttribute("data-set-locale");
    if (loc === "tr" || loc === "en") setLocale(loc);
  });
}

export function attachGlobal(): void {
  if (typeof window === "undefined") return;
  const api = { getLocale, setLocale, t, applyDocumentI18n, initI18n, LOCALES, DEFAULT_LOCALE };
  (window as Window & { LumosI18n?: typeof api }).LumosI18n = api;
}

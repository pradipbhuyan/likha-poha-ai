import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import enLanding from "./locales/en/landing.json";
import hiLanding from "./locales/hi/landing.json";
import enPricing from "./locales/en/pricing.json";
import hiPricing from "./locales/hi/pricing.json";
import enLegal from "./locales/en/legal.json";
import hiLegal from "./locales/hi/legal.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { landing: enLanding, pricing: enPricing, legal: enLegal },
      hi: { landing: hiLanding, pricing: hiPricing, legal: hiLegal },
    },
    ns: ["landing", "pricing", "legal"],
    defaultNS: "landing",
    fallbackLng: "en",
    supportedLngs: ["en", "hi"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage"],
      lookupLocalStorage: "likhapoha_lang",
      caches: ["localStorage"],
    },
  });

export default i18n;

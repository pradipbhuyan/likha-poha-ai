import { useEffect, useState } from "react";
import { useTranslation, Trans } from "react-i18next";
import logoImg from "../assets/AITutorLogo1.png";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const FALLBACK_EMAIL = "likhapohaai@gmail.com";
const LINK_STYLE = { color: "#93c5fd" };

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#f8fafc", marginBottom: 10, borderLeft: "3px solid #6366f1", paddingLeft: 14 }}>
        {title}
      </h2>
      <div style={{ color: "#cbd5e1", fontSize: ".93rem", lineHeight: 1.8, paddingLeft: 17 }}>
        {children}
      </div>
    </div>
  );
}

function LangSwitch({ i18n }) {
  const active = { background: "linear-gradient(135deg,#4d41c5,#5a84e6)", color: "#fff" };
  const base = { border: "none", background: "transparent", color: "#8b96a8", fontFamily: "inherit", fontSize: ".78rem", fontWeight: 700, padding: "6px 13px", borderRadius: 99, cursor: "pointer" };
  return (
    <div style={{ display: "flex", border: "1px solid #334155", borderRadius: 99, padding: 3, gap: 2, background: "#0b1220" }} role="group" aria-label="Language">
      <button type="button" style={i18n.resolvedLanguage === "en" ? { ...base, ...active } : base} onClick={() => i18n.changeLanguage("en")}>EN</button>
      <button type="button" style={i18n.resolvedLanguage === "hi" ? { ...base, ...active } : base} onClick={() => i18n.changeLanguage("hi")}>हिं</button>
    </div>
  );
}

/**
 * Privacy Policy page — accessible at /privacy-policy.
 * No login required.
 *
 * ── Maintenance reminder ──────────────────────────────────────────────────
 * Update this page whenever:
 *   • The grades/audience served changes (currently Grades 5–12)
 *   • New AI providers, third-party services, or integrations are added
 *   • Data retention periods change
 *   • New data types are collected (e.g. voice, device ID)
 *   • Google OAuth scopes change
 *   • A mobile app is launched (add app-specific data collection)
 * See also: RefundPolicyPage.jsx, TermsOfServicePage.jsx
 *
 * Bilingual (EN/HI) via react-i18next, namespace "legal" → key prefix
 * "privacy". Sentences with inline markup (bold, links) use <Trans>, whose
 * children are placeholder elements referenced by position (<0>, <1>, ...)
 * from the translation string in legal.json — the displayed text always
 * comes from that string, not the placeholder's own content. Keep the
 * placeholder count/order in sync with the tag numbers when editing copy.
 *
 * Section 4 (Google Sign-In & Data Usage) is deliberately left in English in
 * both languages — it's the same Google API Services User Data Policy
 * compliance disclosure duplicated from the landing page, and a translated
 * version should go through legal review before shipping rather than being
 * machine-translated here.
 * ─────────────────────────────────────────────────────────────────────────
 */
export default function PrivacyPolicyPage({ onBackToHome }) {
  const { t, i18n } = useTranslation("legal");
  const [contactEmail, setContactEmail] = useState(FALLBACK_EMAIL);

  useEffect(() => {
    fetch(`${API_BASE}/api/payments/contact`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);

  const mailtoLink = <a href={`mailto:${contactEmail}`} style={LINK_STYLE} />;

  return (
    <div style={{ fontFamily: "Inter,'Noto Sans Devanagari',sans-serif", background: "#0f172a", color: "#f8fafc", minHeight: "100vh", lineHeight: 1.7 }}>
      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 40px", background: "rgba(15,23,42,.96)", backdropFilter: "blur(16px)", borderBottom: "1px solid #334155", position: "sticky", top: 0, zIndex: 99, flexWrap: "wrap", gap: 10 }}>
        <button onClick={onBackToHome} style={{ display: "flex", alignItems: "center", gap: "10px", background: "transparent", border: "none", color: "#f8fafc", cursor: "pointer", fontFamily: "inherit" }}>
          <img src={logoImg} alt="Likha Poha AI" style={{ width: 42, height: 42, borderRadius: 10, objectFit: "cover", background: "#fff" }} />
          <span style={{ fontSize: "1.08rem", fontWeight: 700 }}>Likha Poha AI</span>
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LangSwitch i18n={i18n} />
          <button onClick={onBackToHome} style={{ background: "transparent", border: "1px solid #334155", color: "#93c5fd", padding: "8px 18px", borderRadius: 8, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
            {t("common.backToHome")}
          </button>
        </div>
      </nav>

      {/* Content */}
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "60px 24px 80px" }}>
        <div style={{ marginBottom: 40 }}>
          <p style={{ fontSize: ".75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".1em", color: "#93c5fd", marginBottom: 10 }}>{t("common.legalEyebrow")}</p>
          <h1 style={{ fontSize: "clamp(2rem,5vw,3rem)", fontWeight: 900, lineHeight: 1.1, marginBottom: 16 }}>{t("privacy.title")}</h1>
          <p style={{ color: "#94a3b8", fontSize: ".9rem" }}>{t("common.lastUpdated")} &nbsp;·&nbsp; {t("common.effective")}</p>
        </div>

        <Section title={t("privacy.s1.title")}>
          <Trans t={t} i18nKey="privacy.s1.p1"><strong /></Trans>
          <br /><br />
          {t("privacy.s1.p2")}
        </Section>

        <Section title={t("privacy.s2.title")}>
          <strong>{t("privacy.s2.sub1Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            {t("privacy.s2.items1", { returnObjects: true }).map((item, i) => <li key={i}>{item}</li>)}
          </ul>

          <strong>{t("privacy.s2.sub2Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            {t("privacy.s2.items2", { returnObjects: true }).map((item, i) => <li key={i}>{item}</li>)}
          </ul>

          <strong>{t("privacy.s2.sub3Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li>{t("privacy.s2.item3_0")}</li>
            <li>{t("privacy.s2.item3_1")}</li>
            <li><Trans t={t} i18nKey="privacy.s2.item3_2"><strong /></Trans></li>
          </ul>

          <strong>{t("privacy.s2.sub4Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("privacy.s2.items4", { returnObjects: true }).map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        </Section>

        <Section title={t("privacy.s3.title")}>
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            {[0, 1, 2, 3, 4].map(i => (
              <li style={{ marginBottom: 8 }} key={i}>
                <Trans t={t} i18nKey={`privacy.s3.items.${i}`}><strong /></Trans>
              </li>
            ))}
          </ul>
          <Trans t={t} i18nKey="privacy.s3.closing"><strong /></Trans>
        </Section>

        {/* Section 4 — Google Sign-In & Data Usage. Deliberately hardcoded in
            English (see file header comment) rather than translated. */}
        <Section title="4. Google Sign-In & Data Usage">
          Likha Poha AI uses Google Sign-In <strong>only to securely authenticate users</strong>. When you sign in with Google, we request only the following basic profile information:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li>Your name</li>
            <li>Your email address</li>
            <li>Your profile picture</li>
          </ul>
          We use this information <strong>only to</strong>:
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 12 }}>
            <li style={{ marginBottom: 6 }}>Create and identify your account</li>
            <li style={{ marginBottom: 6 }}>Keep you securely logged in</li>
            <li style={{ marginBottom: 6 }}>Personalise your learning experience</li>
            <li>Save your study progress</li>
          </ul>
          <div style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.25)", borderRadius: 8, padding: "12px 16px", marginTop: 12 }}>
            <strong style={{ color: "#fca5a5" }}>Likha Poha AI does NOT:</strong>
            <ul style={{ paddingLeft: 24, marginTop: 8, color: "#cbd5e1" }}>
              <li style={{ marginBottom: 6 }}>Access Gmail, Google Drive, Google Calendar, Google Contacts, or any other Google service</li>
              <li style={{ marginBottom: 6 }}>Sell, share, or transfer Google user data for advertising, marketing, or any commercial purpose</li>
              <li style={{ marginBottom: 6 }}>Use Google user data to train AI or machine learning models</li>
              <li>Request any Google permission beyond basic profile (email + name + picture)</li>
            </ul>
          </div>
          <br />
          Our use of Google user data complies with the{" "}
          <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer" style={{ color: "#93c5fd" }}>
            Google API Services User Data Policy
          </a>, including the Limited Use requirements.
        </Section>

        <Section title={t("privacy.s5.title")}>
          {t("privacy.s5.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("privacy.s5.items", { returnObjects: true }).map((item, i) => <li key={i}>{item}</li>)}
          </ul>
          <Trans t={t} i18nKey="privacy.s5.mid"><strong /></Trans>
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li><a href="https://openai.com/privacy" target="_blank" rel="noreferrer" style={LINK_STYLE}>{t("privacy.s5.links.0")}</a></li>
            <li><a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer" style={LINK_STYLE}>{t("privacy.s5.links.1")}</a></li>
            <li><a href="https://groq.com/privacy-policy" target="_blank" rel="noreferrer" style={LINK_STYLE}>{t("privacy.s5.links.2")}</a></li>
          </ul>
          <br />
          {t("privacy.s5.alsoUse")}
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            {[0, 1, 2, 3].map(i => (
              <li key={i}><Trans t={t} i18nKey={`privacy.s5.vendors.${i}`}><strong /></Trans></li>
            ))}
          </ul>
        </Section>

        <Section title={t("privacy.s6.title")}>
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            {t("privacy.s6.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 8 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
        </Section>

        <Section title={t("privacy.s7.title")}>
          {t("privacy.s7.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("privacy.s7.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 8 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
        </Section>

        <Section title={t("privacy.s8.title")}>
          {t("privacy.s8.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("privacy.s8.items", { returnObjects: true }).map((item, i) => <li key={i}>{item}</li>)}
          </ul>
          {t("privacy.s8.closing")}
        </Section>

        <Section title={t("privacy.s9.title")}>
          {t("privacy.s9.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {[0, 1, 2, 3, 4].map(i => (
              <li style={i < 4 ? { marginBottom: 8 } : undefined} key={i}>
                <Trans t={t} i18nKey={`privacy.s9.items.${i}`}><strong /></Trans>
              </li>
            ))}
          </ul>
          <Trans t={t} i18nKey="privacy.s9.closing" values={{ email: contactEmail }}>{mailtoLink}</Trans>
        </Section>

        <Section title={t("privacy.s10.title")}>
          {t("privacy.s10.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("privacy.s10.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 8 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
          <Trans t={t} i18nKey="privacy.s10.closing" values={{ email: contactEmail }}>{mailtoLink}</Trans>
        </Section>

        <Section title={t("privacy.s11.title")}>
          {t("privacy.s11.body")}
        </Section>

        <Section title={t("privacy.s12.title")}>
          {t("privacy.s12.intro")}
          <br /><br />
          <strong>{t("common.brand")}</strong><br />
          {t("common.emailLabel")}{" "}<a href={`mailto:${contactEmail}`} style={LINK_STYLE}>{contactEmail}</a><br />
          {t("common.websiteLabel")} <a href="https://www.likhapoha.in" style={LINK_STYLE}>www.likhapoha.in</a>
        </Section>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #334155", paddingTop: 32, marginTop: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
          <a href="/terms-of-service" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerTerms")}</a>
          <a href="/refund-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerRefund")}</a>
          <a href="/" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerHome")}</a>
        </div>
      </div>
    </div>
  );
}

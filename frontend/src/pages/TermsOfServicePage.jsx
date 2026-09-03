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
 * Terms of Service page — accessible at /terms-of-service.
 * No login required.
 *
 * ── Maintenance reminder ──────────────────────────────────────────────────
 * Update this page whenever:
 *   • Subscription plan names, prices, or durations change
 *   • The grades/audience served changes (currently Grades 5–12)
 *   • New features or product areas are launched (add to Section 2)
 *   • Acceptable use rules change (Section 5)
 *   • The governing jurisdiction, operator name, or contact changes
 *   • A mobile app is launched or removed
 * See also: RefundPolicyPage.jsx, PrivacyPolicyPage.jsx
 *
 * Bilingual (EN/HI) via react-i18next, namespace "legal" → key prefix "terms".
 * Sentences with inline markup (bold, links) use <Trans>, whose children are
 * placeholder elements referenced by position (<0>, <1>, ...) from the
 * translation string in legal.json — the displayed text always comes from
 * that string, not the placeholder's own content. Keep the placeholder
 * count/order in sync with the tag numbers when editing copy.
 * ─────────────────────────────────────────────────────────────────────────
 */
export default function TermsOfServicePage({ onBackToHome }) {
  const { t, i18n } = useTranslation("legal");
  const [contactEmail, setContactEmail] = useState(FALLBACK_EMAIL);

  useEffect(() => {
    fetch(`${API_BASE}/api/payments/contact`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);

  const mailtoLink = <a href={`mailto:${contactEmail}`} style={LINK_STYLE} />;
  const privacyLink = <a href="/privacy-policy" style={LINK_STYLE} />;
  const refundLink = <a href="/refund-policy" style={LINK_STYLE} />;
  const pricingLink = <a href="/#pricing" style={LINK_STYLE} />;

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
          <h1 style={{ fontSize: "clamp(2rem,5vw,3rem)", fontWeight: 900, lineHeight: 1.1, marginBottom: 16 }}>{t("terms.title")}</h1>
          <p style={{ color: "#94a3b8", fontSize: ".9rem" }}>{t("common.lastUpdated")} &nbsp;·&nbsp; {t("common.effective")}</p>
        </div>

        <Section title={t("terms.s1.title")}>
          <Trans t={t} i18nKey="terms.s1.p1"><strong />{privacyLink}</Trans>
          <br /><br />
          {t("terms.s1.p2")}
        </Section>

        <Section title={t("terms.s2.title")}>
          {t("terms.s2.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("terms.s2.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
          {t("terms.s2.closing")}
        </Section>

        <Section title={t("terms.s3.title")}>
          <strong>{t("terms.s3.sub1Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            {t("terms.s3.items1", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>

          <strong>{t("terms.s3.sub2Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li style={{ marginBottom: 6 }}>{t("terms.s3.item2_0")}</li>
            <li style={{ marginBottom: 6 }}><Trans t={t} i18nKey="terms.s3.item2_1" values={{ email: contactEmail }}>{mailtoLink}</Trans></li>
            <li>{t("terms.s3.item2_2")}</li>
          </ul>

          <strong>{t("terms.s3.sub3Title")}</strong>
          <br />
          {t("terms.s3.sub3Body")}
        </Section>

        <Section title={t("terms.s4.title")}>
          <strong>{t("terms.s4.sub1Title")}</strong>
          <br />
          <Trans t={t} i18nKey="terms.s4.sub1Body"><strong /><strong />{pricingLink}</Trans>

          <br /><br />
          <strong>{t("terms.s4.sub2Title")}</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            {t("terms.s4.items2", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>

          <strong>{t("terms.s4.sub3Title")}</strong>
          <br />
          <Trans t={t} i18nKey="terms.s4.sub3Body">{refundLink}</Trans>
        </Section>

        <Section title={t("terms.s5.title")}>
          {t("terms.s5.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("terms.s5.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
          {t("terms.s5.closing")}
        </Section>

        <Section title={t("terms.s6.title")}>
          {t("terms.s6.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>{t("terms.s6.item0")}</li>
            <li style={{ marginBottom: 6 }}><Trans t={t} i18nKey="terms.s6.item1"><strong /></Trans></li>
            <li style={{ marginBottom: 6 }}>{t("terms.s6.item2")}</li>
            <li>{t("terms.s6.item3")}</li>
          </ul>
        </Section>

        <Section title={t("terms.s7.title")}>
          <strong>{t("terms.s7.sub1Title")}</strong>
          <br />
          {t("terms.s7.sub1Body")}

          <br /><br />
          <strong>{t("terms.s7.sub2Title")}</strong>
          <br />
          {t("terms.s7.sub2Body")}

          <br /><br />
          <strong>{t("terms.s7.sub3Title")}</strong>
          <br />
          {t("terms.s7.sub3Body")}
        </Section>

        <Section title={t("terms.s8.title")}>
          <Trans t={t} i18nKey="terms.s8.body">{privacyLink}</Trans>
        </Section>

        <Section title={t("terms.s9.title")}>
          {t("terms.s9.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("terms.s9.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
        </Section>

        <Section title={t("terms.s10.title")}>
          {t("terms.s10.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("terms.s10.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
        </Section>

        <Section title={t("terms.s11.title")}>
          {t("terms.s11.intro")}
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            {t("terms.s11.items", { returnObjects: true }).map((item, i, arr) => (
              <li style={i < arr.length - 1 ? { marginBottom: 6 } : undefined} key={i}>{item}</li>
            ))}
          </ul>
          {t("terms.s11.closing")}
        </Section>

        <Section title={t("terms.s12.title")}>
          {t("terms.s12.p1")}
          <br /><br />
          <Trans t={t} i18nKey="terms.s12.p2" values={{ email: contactEmail }}>{mailtoLink}</Trans>
        </Section>

        <Section title={t("terms.s13.title")}>
          {t("terms.s13.body")}
        </Section>

        <Section title={t("terms.s14.title")}>
          {t("terms.s14.intro")}
          <br /><br />
          <strong>{t("common.brand")}</strong><br />
          {t("common.emailLabel")}{" "}<a href={`mailto:${contactEmail}`} style={LINK_STYLE}>{contactEmail}</a><br />
          {t("common.websiteLabel")} <a href="https://www.likhapoha.in" style={LINK_STYLE}>www.likhapoha.in</a>
        </Section>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #334155", paddingTop: 32, marginTop: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
          <a href="/privacy-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerPrivacy")}</a>
          <a href="/refund-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerRefund")}</a>
          <a href="/" style={{ color: "#93c5fd", fontSize: ".88rem" }}>{t("common.footerHome")}</a>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { useTranslation, Trans } from "react-i18next";
import logoImg from "../assets/AITutorLogo1.png";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const FALLBACK_EMAIL = "likhapohaai@gmail.com";
const LINK_STYLE = { color: "#93c5fd" };

/**
 * Standalone Refund Policy page accessible at /refund-policy.
 * Rendered outside the authenticated app shell — no login required.
 * Contact email is fetched from /api/payments/contact (subscription settings)
 * so it never needs to be hardcoded here.
 *
 * ── Maintenance reminder ──────────────────────────────────────────────────
 * Update this page whenever:
 *   • Subscription plan names, prices, or durations change
 *   • The refund window or eligibility criteria change
 *   • New plan types (e.g. annual, family) are added or removed
 *   • The contact email or support process changes
 * See also: TermsOfServicePage.jsx, PrivacyPolicyPage.jsx
 *
 * Bilingual (EN/HI) via react-i18next, namespace "legal" → key prefix "refund".
 * Sentences with inline markup (bold, mailto links) use <Trans>, whose
 * children are placeholder elements referenced by position (<0>, <1>, ...)
 * from the translation string in legal.json — the displayed text always
 * comes from that string, not from the placeholder's own content. Keep the
 * placeholder count/order in sync with the tag numbers when editing copy.
 * ─────────────────────────────────────────────────────────────────────────
 */
export default function RefundPolicyPage({ onBackToHome }) {
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
    <div style={{fontFamily:"Inter,'Noto Sans Devanagari',sans-serif",background:"#0f172a",color:"#f8fafc",minHeight:"100vh",lineHeight:1.7}}>
      <nav style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"14px 40px",background:"rgba(15,23,42,.96)",backdropFilter:"blur(16px)",borderBottom:"1px solid #334155",position:"sticky",top:0,zIndex:99,flexWrap:"wrap",gap:10}}>
        <button onClick={onBackToHome} style={{display:"flex",alignItems:"center",gap:"10px",background:"transparent",border:"none",color:"#f8fafc",cursor:"pointer",fontFamily:"inherit"}}>
          <img src={logoImg} alt="Likha Poha AI" style={{width:42,height:42,borderRadius:10,objectFit:"cover",background:"#fff"}} />
          <span style={{fontSize:"1.08rem",fontWeight:700}}>Likha Poha AI</span>
        </button>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <LangSwitch i18n={i18n} />
          <button onClick={onBackToHome} style={{background:"transparent",border:"1px solid #334155",color:"#93c5fd",padding:"8px 18px",borderRadius:8,fontSize:".88rem",cursor:"pointer",fontFamily:"inherit"}}>
            {t("common.backToHome")}
          </button>
        </div>
      </nav>

      <div style={{maxWidth:800,margin:"0 auto",padding:"60px 24px 80px"}}>
        <div style={{marginBottom:40}}>
          <p style={{fontSize:".75rem",fontWeight:700,textTransform:"uppercase",letterSpacing:".1em",color:"#93c5fd",marginBottom:10}}>{t("common.legalEyebrow")}</p>
          <h1 style={{fontSize:"clamp(2rem,5vw,3rem)",fontWeight:900,lineHeight:1.1,marginBottom:16}}>{t("refund.title")}</h1>
          <p style={{color:"#94a3b8",fontSize:".9rem"}}>{t("common.lastUpdated")} &nbsp;·&nbsp; {t("common.effective")}</p>
        </div>

        <Section title={t("refund.s1.title")}>
          <Trans t={t} i18nKey="refund.s1.p1"><strong /></Trans>
          <br /><br />
          {t("refund.s1.p2")}
        </Section>

        <Section title={t("refund.s2.title")}>
          {t("refund.s2.intro")}
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            {[0, 1, 2].map(i => (
              <li style={i < 2 ? {marginBottom:8} : undefined} key={i}>
                <Trans t={t} i18nKey={`refund.s2.items.${i}`}><strong /></Trans>
              </li>
            ))}
          </ul>
          <Trans t={t} i18nKey="refund.s2.freeTier"><strong /></Trans>
          <br /><br />
          {t("refund.s2.closing")}
        </Section>

        <Section title={t("refund.s3.title")}>
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>
              <Trans t={t} i18nKey="refund.s3.items.0" values={{ email: contactEmail }}>
                <strong />{mailtoLink}
              </Trans>
            </li>
            <li style={{marginBottom:8}}>
              <Trans t={t} i18nKey="refund.s3.items.1"><strong /><strong /></Trans>
            </li>
            <li style={{marginBottom:8}}>
              <Trans t={t} i18nKey="refund.s3.items.2"><strong /></Trans>
            </li>
            <li>
              <Trans t={t} i18nKey="refund.s3.items.3"><strong /></Trans>
            </li>
          </ul>
        </Section>

        <Section title={t("refund.s4.title")}>
          <Trans t={t} i18nKey="refund.s4.intro" values={{ email: contactEmail }}>{mailtoLink}</Trans>
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>{t("refund.s4.items.0")}</li>
            <li style={{marginBottom:8}}>{t("refund.s4.items.1")}</li>
            <li>{t("refund.s4.items.2")}</li>
          </ul>
          <br />
          <Trans t={t} i18nKey="refund.s4.closing"><strong /><strong /></Trans>
        </Section>

        <Section title={t("refund.s5.title")}>
          <Trans t={t} i18nKey="refund.s5.intro"><strong /></Trans>
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>{t("refund.s5.items.0")}</li>
            <li style={{marginBottom:8}}>{t("refund.s5.items.1")}</li>
            <li style={{marginBottom:8}}>{t("refund.s5.items.2")}</li>
            <li>{t("refund.s5.items.3")}</li>
          </ul>
        </Section>

        <Section title={t("refund.s6.title")}>
          <Trans t={t} i18nKey="refund.s6.body" values={{ email: contactEmail }}>{mailtoLink}</Trans>
        </Section>

        <Section title={t("refund.s7.title")}>
          {t("refund.s7.body")}
        </Section>

        <Section title={t("refund.s8.title")}>
          {t("refund.s8.intro")}
          <br /><br />
          <strong>{t("common.brand")}</strong><br />
          {t("common.emailLabel")} <a href={`mailto:${contactEmail}`} style={LINK_STYLE}>{contactEmail}</a><br />
          {t("common.websiteLabel")} <a href="https://www.likhapoha.in" style={LINK_STYLE}>www.likhapoha.in</a>
        </Section>

        <div style={{marginTop:60,paddingTop:24,borderTop:"1px solid #334155",textAlign:"center",color:"#64748b",fontSize:".85rem"}}>
          &copy; {new Date().getFullYear()} Likha Poha AI &middot; {t("common.madeInPre")} ❤ {t("common.madeInPost")}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{marginBottom:36}}>
      <h2 style={{fontSize:"1.15rem",fontWeight:700,color:"#e2e8f0",marginBottom:12,paddingBottom:8,borderBottom:"1px solid #1e293b"}}>{title}</h2>
      <div style={{color:"#cbd5e1",fontSize:".95rem"}}>{children}</div>
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

import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const FALLBACK_EMAIL = "likhapohaai@gmail.com";

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
 * ─────────────────────────────────────────────────────────────────────────
 */
export default function PrivacyPolicyPage({ onBackToHome }) {
  const [contactEmail, setContactEmail] = useState(FALLBACK_EMAIL);

  useEffect(() => {
    fetch(`${API_BASE}/api/payments/contact`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);

  return (
    <div style={{ fontFamily: "Inter,sans-serif", background: "#0f172a", color: "#f8fafc", minHeight: "100vh", lineHeight: 1.7 }}>
      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 40px", background: "rgba(15,23,42,.96)", backdropFilter: "blur(16px)", borderBottom: "1px solid #334155", position: "sticky", top: 0, zIndex: 99 }}>
        <button onClick={onBackToHome} style={{ display: "flex", alignItems: "center", gap: "10px", background: "transparent", border: "none", color: "#f8fafc", cursor: "pointer", fontFamily: "inherit" }}>
          <img src={logoImg} alt="Likha Poha AI" style={{ width: 42, height: 42, borderRadius: 10, objectFit: "cover", background: "#fff" }} />
          <span style={{ fontSize: "1.08rem", fontWeight: 700 }}>Likha Poha AI</span>
        </button>
        <button onClick={onBackToHome} style={{ background: "transparent", border: "1px solid #334155", color: "#93c5fd", padding: "8px 18px", borderRadius: 8, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          ← Back to Home
        </button>
      </nav>

      {/* Content */}
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "60px 24px 80px" }}>
        <div style={{ marginBottom: 40 }}>
          <p style={{ fontSize: ".75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".1em", color: "#93c5fd", marginBottom: 10 }}>Legal</p>
          <h1 style={{ fontSize: "clamp(2rem,5vw,3rem)", fontWeight: 900, lineHeight: 1.1, marginBottom: 16 }}>Privacy Policy</h1>
          <p style={{ color: "#94a3b8", fontSize: ".9rem" }}>Last updated: July 2026 &nbsp;·&nbsp; Effective immediately</p>
        </div>

        <Section title="1. Who We Are">
          Likha Poha AI ("we", "us", or "our") is an AI-powered educational platform for CBSE students in Grades 5–12, accessible at <strong>www.likhapoha.in</strong>. A companion mobile app is also available for Android and iOS.
          <br /><br />
          This Privacy Policy explains what personal data we collect, why we collect it, how we use it, and your rights regarding that data. By using our platform you agree to the practices described here.
        </Section>

        <Section title="2. Information We Collect">
          <strong>2.1 Account Information</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li>Name / username</li>
            <li>Email address</li>
            <li>Password (stored as a bcrypt hash — we never store plain-text passwords)</li>
            <li>Grade, board (CBSE/ICSE/State), and subjects</li>
            <li>Role (student, parent, teacher)</li>
          </ul>

          <strong>2.2 Usage Data</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li>Lessons generated (grade, subject, chapter, step)</li>
            <li>Doubts asked and AI responses</li>
            <li>Mock tests taken and scores</li>
            <li>Token consumption per session</li>
            <li>Page views and feature interactions</li>
          </ul>

          <strong>2.3 Payment Data</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li>Razorpay order ID and payment ID</li>
            <li>Subscription plan selected and payment status</li>
            <li>We do <strong>not</strong> store card numbers, CVV, or bank details — all payment processing is handled by Razorpay.</li>
          </ul>

          <strong>2.4 Technical Data</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li>IP address and browser user-agent (for security logging)</li>
            <li>Request timestamps and response times</li>
            <li>Error logs (anonymised where possible)</li>
            <li>On the mobile app: device type, OS version, and app version (no precise location or contacts accessed)</li>
          </ul>
        </Section>

        <Section title="3. How We Use Your Data">
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            <li style={{ marginBottom: 8 }}><strong>Deliver the service</strong> — generate AI lessons, answer doubts, create mock tests personalised to your grade and curriculum.</li>
            <li style={{ marginBottom: 8 }}><strong>Account management</strong> — create and manage your account, process subscriptions, and send transactional emails (welcome, password reset, receipt).</li>
            <li style={{ marginBottom: 8 }}><strong>Improve the platform</strong> — analyse aggregated usage patterns to improve lesson quality, model performance, and UI/UX.</li>
            <li style={{ marginBottom: 8 }}><strong>Safety and fraud prevention</strong> — detect abuse, enforce rate limits, and protect platform integrity.</li>
            <li style={{ marginBottom: 8 }}><strong>Legal compliance</strong> — maintain records as required by Indian law (IT Act 2000, IT Rules 2021).</li>
          </ul>
          We do <strong>not</strong> sell, rent, or trade your personal data to third parties for marketing.
        </Section>

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

        <Section title="5. AI Providers and Third-Party Services">
          Likha Poha AI uses AI language model providers (OpenAI, Groq, Google Gemini, Cerebras, SambaNova, Anthropic, Ollama Cloud) to generate lesson content. Prompts sent to these providers contain:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li>Grade, subject, chapter, and topic</li>
            <li>The student's question (for Ask Doubt)</li>
          </ul>
          Prompts do <strong>not</strong> contain names, email addresses, or other personally identifiable information. We encourage you to review the privacy policies of these providers:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li><a href="https://openai.com/privacy" target="_blank" rel="noreferrer" style={{ color: "#93c5fd" }}>OpenAI Privacy Policy</a></li>
            <li><a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer" style={{ color: "#93c5fd" }}>Google Privacy Policy (Gemini)</a></li>
            <li><a href="https://groq.com/privacy-policy" target="_blank" rel="noreferrer" style={{ color: "#93c5fd" }}>Groq Privacy Policy</a></li>
          </ul>
          <br />
          We also use:
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            <li><strong>Supabase</strong> — database and authentication (data stored in secure cloud infrastructure)</li>
            <li><strong>Razorpay</strong> — payment processing (PCI-DSS compliant)</li>
            <li><strong>Render</strong> — backend hosting (api.likhapoha.in)</li>
            <li><strong>Vercel</strong> — frontend hosting (www.likhapoha.in)</li>
          </ul>
        </Section>

        <Section title="6. Data Retention">
          <ul style={{ paddingLeft: 24, marginTop: 4 }}>
            <li style={{ marginBottom: 8 }}>Account data is retained for as long as your account is active.</li>
            <li style={{ marginBottom: 8 }}>AI usage logs are retained for 12 months for platform analytics and then deleted.</li>
            <li style={{ marginBottom: 8 }}>Payment records are retained for 7 years as required by Indian tax and financial laws.</li>
            <li>On account deletion, all personal data is removed within 30 days except where legally required to be retained.</li>
          </ul>
        </Section>

        <Section title="7. Children's Privacy">
          Likha Poha AI is designed for students in Grades 5–12 (approximately ages 10–18). We take children's privacy seriously:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 8 }}>Student accounts are created by parents or guardians via the Family Account system, or directly by school administrators.</li>
            <li style={{ marginBottom: 8 }}>We do not show advertisements to students.</li>
            <li style={{ marginBottom: 8 }}>We do not collect more data than necessary for delivering the educational service.</li>
            <li>Parents may request deletion of their child's account and data at any time by contacting us.</li>
          </ul>
        </Section>

        <Section title="8. Cookies and Local Storage">
          We use browser local storage (not third-party cookies) to:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li>Maintain your login session (JWT token)</li>
            <li>Remember your dark/light mode preference</li>
            <li>Cache recently viewed lesson content for faster loading</li>
          </ul>
          We do not use advertising cookies or third-party tracking pixels.
        </Section>

        <Section title="9. Your Rights (PDPB / IT Act)">
          Under Indian data protection law and our commitments, you have the right to:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 8 }}><strong>Access</strong> — request a copy of the data we hold about you.</li>
            <li style={{ marginBottom: 8 }}><strong>Correction</strong> — update incorrect or incomplete data via your profile settings.</li>
            <li style={{ marginBottom: 8 }}><strong>Deletion</strong> — request deletion of your account and associated data.</li>
            <li style={{ marginBottom: 8 }}><strong>Portability</strong> — request an export of your usage data in a structured format.</li>
            <li><strong>Withdraw consent</strong> — you may stop using the service at any time.</li>
          </ul>
          To exercise any right, write to us at{" "}
          <a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a>.
          We will respond within 30 days.
        </Section>

        <Section title="10. Data Security">
          We implement industry-standard security measures:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 8 }}>All data in transit is encrypted via TLS 1.2+.</li>
            <li style={{ marginBottom: 8 }}>Passwords are hashed using bcrypt (never stored in plain text).</li>
            <li style={{ marginBottom: 8 }}>API keys and secrets are stored as environment variables or in encrypted Supabase columns — never in source code.</li>
            <li style={{ marginBottom: 8 }}>Admin access requires multi-layer authentication.</li>
            <li>We conduct periodic security reviews of our infrastructure.</li>
          </ul>
          No system is perfectly secure. If you discover a security vulnerability, please report it responsibly to{" "}
          <a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a>.
        </Section>

        <Section title="11. Changes to This Policy">
          We may update this Privacy Policy periodically. When we do, we will update the "Last updated" date at the top and, for material changes, notify you via email or an in-app notice. Continued use of the platform after changes constitutes acceptance of the updated policy.
        </Section>

        <Section title="12. Contact Us">
          For privacy-related questions, requests, or concerns:
          <br /><br />
          <strong>Likha Poha AI</strong><br />
          Email:{" "}<a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a><br />
          Website: <a href="https://www.likhapoha.in" style={{ color: "#93c5fd" }}>www.likhapoha.in</a>
        </Section>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #334155", paddingTop: 32, marginTop: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
          <a href="/terms-of-service" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Terms of Service</a>
          <a href="/refund-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Refund Policy</a>
          <a href="/" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Home</a>
        </div>
      </div>
    </div>
  );
}

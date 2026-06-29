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
 * Terms of Service page — accessible at /terms-of-service.
 * No login required.
 */
export default function TermsOfServicePage({ onBackToHome }) {
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
          <img src={logoImg} alt="LikhaPoha AI" style={{ width: 42, height: 42, borderRadius: 10, objectFit: "cover", background: "#fff" }} />
          <span style={{ fontSize: "1.08rem", fontWeight: 700 }}>LikhaPoha AI</span>
        </button>
        <button onClick={onBackToHome} style={{ background: "transparent", border: "1px solid #334155", color: "#93c5fd", padding: "8px 18px", borderRadius: 8, fontSize: ".88rem", cursor: "pointer", fontFamily: "inherit" }}>
          ← Back to Home
        </button>
      </nav>

      {/* Content */}
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "60px 24px 80px" }}>
        <div style={{ marginBottom: 40 }}>
          <p style={{ fontSize: ".75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".1em", color: "#93c5fd", marginBottom: 10 }}>Legal</p>
          <h1 style={{ fontSize: "clamp(2rem,5vw,3rem)", fontWeight: 900, lineHeight: 1.1, marginBottom: 16 }}>Terms of Service</h1>
          <p style={{ color: "#94a3b8", fontSize: ".9rem" }}>Last updated: June 2026 &nbsp;·&nbsp; Effective immediately</p>
        </div>

        <Section title="1. Acceptance of Terms">
          By accessing or using LikhaPoha AI ("the Platform", "we", "us", or "our") at <strong>www.likhapoha.in</strong>, you agree to be bound by these Terms of Service ("Terms") and our{" "}
          <a href="/privacy-policy" style={{ color: "#93c5fd" }}>Privacy Policy</a>. If you do not agree to these Terms, please do not use the Platform.
          <br /><br />
          These Terms constitute a legally binding agreement between you (the user) and LikhaPoha AI, operated by Pradip Bhuyan, India.
        </Section>

        <Section title="2. Description of Service">
          LikhaPoha AI provides AI-powered educational tools for CBSE students in Classes 5–10, including:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>AI-generated step-by-step lessons aligned to NCERT curriculum</li>
            <li style={{ marginBottom: 6 }}>Ask Doubt — conversational AI answers to student questions</li>
            <li style={{ marginBottom: 6 }}>Mock Test Studio — customisable CBSE practice tests with 70,000+ questions</li>
            <li style={{ marginBottom: 6 }}>Formula Explorer — chapter-wise formula sheets with worked examples</li>
            <li>AI Tutor — personalised learning guidance</li>
          </ul>
          We reserve the right to modify, suspend, or discontinue any feature of the Platform at any time with reasonable notice.
        </Section>

        <Section title="3. Eligibility and Accounts">
          <strong>3.1 Eligibility</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li style={{ marginBottom: 6 }}>The Platform is designed for students in Classes 5–10 (approximately ages 10–16).</li>
            <li style={{ marginBottom: 6 }}>Users under 18 must have parental consent. Parents/guardians are responsible for their child's use of the Platform.</li>
            <li>You must provide accurate and complete information when creating an account.</li>
          </ul>

          <strong>3.2 Account Security</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li style={{ marginBottom: 6 }}>You are responsible for maintaining the confidentiality of your login credentials.</li>
            <li style={{ marginBottom: 6 }}>You must notify us immediately at{" "}<a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a> if you suspect unauthorised access to your account.</li>
            <li>Sharing your account credentials with others is not permitted.</li>
          </ul>

          <strong>3.3 One Account Per User</strong>
          <br />
          Each person may maintain only one active account. Creating multiple accounts to circumvent usage limits or subscription restrictions is prohibited.
        </Section>

        <Section title="4. Subscriptions and Payments">
          <strong>4.1 Plans</strong>
          <br />
          LikhaPoha AI offers both free and paid subscription plans. Paid plans are billed monthly. Plan features and pricing are described on the{" "}
          <a href="/#pricing" style={{ color: "#93c5fd" }}>Pricing page</a>.

          <br /><br />
          <strong>4.2 Billing</strong>
          <ul style={{ paddingLeft: 24, marginTop: 8, marginBottom: 16 }}>
            <li style={{ marginBottom: 6 }}>Payments are processed by Razorpay, a PCI-DSS compliant payment gateway.</li>
            <li style={{ marginBottom: 6 }}>All amounts are in Indian Rupees (INR) and inclusive of applicable taxes.</li>
            <li>Subscriptions do not auto-renew — you choose to extend when your plan expires.</li>
          </ul>

          <strong>4.3 Refunds</strong>
          <br />
          Please refer to our{" "}
          <a href="/refund-policy" style={{ color: "#93c5fd" }}>Refund Policy</a> for details on eligibility, timelines, and the refund process.
        </Section>

        <Section title="5. Acceptable Use">
          You agree to use the Platform only for lawful educational purposes and in accordance with these Terms. You must not:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>Use the Platform to generate, store, or share content that is harmful, abusive, defamatory, or illegal.</li>
            <li style={{ marginBottom: 6 }}>Attempt to reverse-engineer, copy, scrape, or harvest content, lesson data, or question banks from the Platform.</li>
            <li style={{ marginBottom: 6 }}>Use automated scripts, bots, or crawlers to access the Platform without our written permission.</li>
            <li style={{ marginBottom: 6 }}>Attempt to bypass subscription limits, rate limits, or access controls.</li>
            <li style={{ marginBottom: 6 }}>Upload or transmit malicious code, viruses, or any software designed to disrupt the Platform.</li>
            <li style={{ marginBottom: 6 }}>Impersonate another user, teacher, or administrator.</li>
            <li>Use the Platform for commercial tutoring services or reselling AI-generated content without our written consent.</li>
          </ul>
          Violation of these rules may result in immediate account suspension without refund.
        </Section>

        <Section title="6. AI-Generated Content Disclaimer">
          LikhaPoha AI uses large language models to generate educational content. While we work to ensure quality and curriculum alignment:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>AI-generated lessons, answers, and explanations may occasionally contain errors, inaccuracies, or outdated information.</li>
            <li style={{ marginBottom: 6 }}>Content should be used as a <strong>supplementary learning aid</strong>, not as a substitute for verified textbooks, teachers, or official NCERT materials.</li>
            <li style={{ marginBottom: 6 }}>For competitive exams or high-stakes assessments, always verify answers with authoritative sources.</li>
            <li>We continuously improve content quality through human review and AI model upgrades.</li>
          </ul>
        </Section>

        <Section title="7. Intellectual Property">
          <strong>7.1 Our Content</strong>
          <br />
          All platform design, code, branding, lesson templates, question banks, and AI model configurations are the intellectual property of LikhaPoha AI. You may not reproduce, distribute, or create derivative works from our content without prior written permission.

          <br /><br />
          <strong>7.2 NCERT Curriculum</strong>
          <br />
          Lesson topics and chapter names are based on the publicly available NCERT curriculum published by the Government of India. We acknowledge NCERT's role in shaping the Indian educational framework.

          <br /><br />
          <strong>7.3 Your Content</strong>
          <br />
          Any content you submit (e.g. doubt questions, feedback) grants us a non-exclusive, royalty-free licence to use it to improve the Platform. We will not identify you personally in any such use.
        </Section>

        <Section title="8. Privacy">
          Your use of the Platform is also governed by our{" "}
          <a href="/privacy-policy" style={{ color: "#93c5fd" }}>Privacy Policy</a>, which is incorporated into these Terms by reference. By using the Platform, you consent to the data practices described therein.
        </Section>

        <Section title="9. Limitation of Liability">
          To the maximum extent permitted by applicable law:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>LikhaPoha AI is provided "as is" without warranties of any kind, express or implied.</li>
            <li style={{ marginBottom: 6 }}>We do not guarantee that the Platform will be error-free, uninterrupted, or always available.</li>
            <li style={{ marginBottom: 6 }}>We are not liable for any loss of data, academic performance outcomes, or indirect, incidental, or consequential damages arising from use of the Platform.</li>
            <li>Our total liability to you in any circumstances shall not exceed the amount paid by you in the 30 days preceding the claim.</li>
          </ul>
        </Section>

        <Section title="10. Indemnification">
          You agree to indemnify and hold harmless LikhaPoha AI, its operators, employees, and partners from any claims, damages, or expenses (including legal fees) arising from:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>Your violation of these Terms</li>
            <li style={{ marginBottom: 6 }}>Your misuse of the Platform</li>
            <li>Any content you submit to the Platform</li>
          </ul>
        </Section>

        <Section title="11. Termination">
          We may suspend or terminate your account at any time if:
          <ul style={{ paddingLeft: 24, marginTop: 8 }}>
            <li style={{ marginBottom: 6 }}>You violate these Terms or our Acceptable Use policy.</li>
            <li style={{ marginBottom: 6 }}>We detect fraudulent activity or abuse of platform resources.</li>
            <li>You request account deletion.</li>
          </ul>
          Upon termination, your right to access the Platform ceases immediately. Provisions of these Terms that by their nature should survive termination (including intellectual property, limitation of liability, and governing law) will continue to apply.
        </Section>

        <Section title="12. Governing Law and Disputes">
          These Terms are governed by the laws of India. Any disputes arising under these Terms shall be subject to the exclusive jurisdiction of the courts of Assam, India.
          <br /><br />
          Before initiating formal legal proceedings, we encourage you to contact us at{" "}
          <a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a> to resolve the matter amicably.
        </Section>

        <Section title="13. Changes to Terms">
          We reserve the right to modify these Terms at any time. Updated Terms will be posted on this page with a new "Last updated" date. For material changes, we will notify registered users via email at least 7 days before the changes take effect. Continued use of the Platform after the effective date constitutes your acceptance of the updated Terms.
        </Section>

        <Section title="14. Contact">
          If you have questions about these Terms of Service:
          <br /><br />
          <strong>LikhaPoha AI</strong><br />
          Email:{" "}<a href={`mailto:${contactEmail}`} style={{ color: "#93c5fd" }}>{contactEmail}</a><br />
          Website: <a href="https://www.likhapoha.in" style={{ color: "#93c5fd" }}>www.likhapoha.in</a>
        </Section>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #334155", paddingTop: 32, marginTop: 24, display: "flex", gap: 24, flexWrap: "wrap" }}>
          <a href="/privacy-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Privacy Policy</a>
          <a href="/refund-policy" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Refund Policy</a>
          <a href="/" style={{ color: "#93c5fd", fontSize: ".88rem" }}>Home</a>
        </div>
      </div>
    </div>
  );
}

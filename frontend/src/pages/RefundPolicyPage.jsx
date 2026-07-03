import { useEffect, useState } from "react";
import logoImg from "../assets/AITutorLogo1.png";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const FALLBACK_EMAIL = "likhapohaai@gmail.com";

/**
 * Standalone Refund Policy page accessible at /refund-policy.
 * Rendered outside the authenticated app shell — no login required.
 * Contact email is fetched from /api/payments/contact (subscription settings)
 * so it never needs to be hardcoded here.
 */
export default function RefundPolicyPage({ onBackToHome }) {
  const [contactEmail, setContactEmail] = useState(FALLBACK_EMAIL);

  useEffect(() => {
    fetch(`${API_BASE}/api/payments/contact`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.email) setContactEmail(data.email); })
      .catch(() => {});
  }, []);

  return (
    <div style={{fontFamily:"Inter,sans-serif",background:"#0f172a",color:"#f8fafc",minHeight:"100vh",lineHeight:1.7}}>
      <nav style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"14px 40px",background:"rgba(15,23,42,.96)",backdropFilter:"blur(16px)",borderBottom:"1px solid #334155",position:"sticky",top:0,zIndex:99}}>
        <button onClick={onBackToHome} style={{display:"flex",alignItems:"center",gap:"10px",background:"transparent",border:"none",color:"#f8fafc",cursor:"pointer",fontFamily:"inherit"}}>
          <img src={logoImg} alt="Likha Poha AI" style={{width:42,height:42,borderRadius:10,objectFit:"cover",background:"#fff"}} />
          <span style={{fontSize:"1.08rem",fontWeight:700}}>Likha Poha AI</span>
        </button>
        <button onClick={onBackToHome} style={{background:"transparent",border:"1px solid #334155",color:"#93c5fd",padding:"8px 18px",borderRadius:8,fontSize:".88rem",cursor:"pointer",fontFamily:"inherit"}}>
          ← Back to Home
        </button>
      </nav>

      <div style={{maxWidth:800,margin:"0 auto",padding:"60px 24px 80px"}}>
        <div style={{marginBottom:40}}>
          <p style={{fontSize:".75rem",fontWeight:700,textTransform:"uppercase",letterSpacing:".1em",color:"#93c5fd",marginBottom:10}}>Legal</p>
          <h1 style={{fontSize:"clamp(2rem,5vw,3rem)",fontWeight:900,lineHeight:1.1,marginBottom:16}}>Refund Policy</h1>
          <p style={{color:"#94a3b8",fontSize:".9rem"}}>Last updated: June 2026 &nbsp;·&nbsp; Effective immediately</p>
        </div>

        <Section title="1. Overview">
          Likha Poha AI ("we", "us", or "our") offers AI-powered educational services for CBSE students in Classes 5–10. This Refund Policy explains when and how refunds are issued for subscription fees paid on our platform at <strong>www.likhapoha.in</strong>.
          <br /><br />
          By subscribing to any paid plan, you agree to this Refund Policy. Please read it carefully before making a purchase.
        </Section>

        <Section title="2. Trial Plan — Premium Nano (₹99 / 8 Days)">
          The ₹99 trial plan is a <strong>paid introductory offer</strong> designed to let you experience the full Likha Poha AI platform at minimal cost before committing to a monthly plan.
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>The trial fee of ₹99 is <strong>non-refundable</strong> once access has been activated.</li>
            <li style={{marginBottom:8}}>If access was not activated due to a technical error on our side, a full refund will be issued within 5–7 business days.</li>
            <li>Trial plans do not auto-renew.</li>
          </ul>
        </Section>

        <Section title="3. Monthly Plans — Premium (₹299/month) and Family Premium (₹499/month)">
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}><strong>Within 24 hours of first purchase:</strong> If you have not used the platform (no lessons generated, no doubts asked, no mock tests taken), you may request a full refund by writing to <a href={`mailto:${contactEmail}`} style={{color:"#93c5fd"}}>{contactEmail}</a>.</li>
            <li style={{marginBottom:8}}><strong>After 24 hours:</strong> Subscriptions are <strong>non-refundable</strong> once the billing cycle has started and platform features have been accessed.</li>
            <li style={{marginBottom:8}}><strong>Recurring billing:</strong> If you wish to cancel, please do so before your next renewal date. Cancellation stops future charges but does not entitle you to a refund for the current billing period already paid.</li>
            <li>If a technical failure on our platform prevented you from accessing paid features for a significant portion of your billing cycle, we will assess each case individually and may issue a prorated credit or refund.</li>
          </ul>
        </Section>

        <Section title="4. How to Request a Refund">
          To request a refund, email us at <a href={`mailto:${contactEmail}`} style={{color:"#93c5fd"}}>{contactEmail}</a> with:
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>Your registered email address or username</li>
            <li style={{marginBottom:8}}>The plan you subscribed to and the date of purchase</li>
            <li>A brief reason for the refund request</li>
          </ul>
          <br />
          We aim to respond within <strong>2 business days</strong>. Approved refunds are processed within <strong>5–7 business days</strong> to the original payment method.
        </Section>

        <Section title="5. Non-Refundable Situations">
          Refunds will <strong>not</strong> be issued in the following cases:
          <ul style={{paddingLeft:24,marginTop:12,color:"#cbd5e1"}}>
            <li style={{marginBottom:8}}>The platform was used (lessons generated, doubts asked, or tests taken)</li>
            <li style={{marginBottom:8}}>The refund request is made after the eligible window</li>
            <li style={{marginBottom:8}}>Account suspension or termination due to a violation of our Terms of Service</li>
            <li>Dissatisfaction due to AI-generated content quality — we encourage using the 8-day trial to evaluate the full platform before upgrading</li>
          </ul>
        </Section>

        <Section title="6. Disputed or Fraudulent Transactions">
          If you believe an unauthorised charge was made to your account, contact us immediately at <a href={`mailto:${contactEmail}`} style={{color:"#93c5fd"}}>{contactEmail}</a>. We will investigate and resolve legitimate disputes as quickly as possible.
        </Section>

        <Section title="7. Changes to This Policy">
          We may update this Refund Policy from time to time. Changes will be posted on this page with an updated effective date. Continued use of the platform after changes constitutes acceptance of the revised policy.
        </Section>

        <Section title="8. Contact Us">
          For any questions about this policy or your subscription:
          <br /><br />
          <strong>Likha Poha AI</strong><br />
          Email: <a href={`mailto:${contactEmail}`} style={{color:"#93c5fd"}}>{contactEmail}</a><br />
          Website: <a href="https://www.likhapoha.in" style={{color:"#93c5fd"}}>www.likhapoha.in</a>
        </Section>

        <div style={{marginTop:60,paddingTop:24,borderTop:"1px solid #334155",textAlign:"center",color:"#64748b",fontSize:".85rem"}}>
          &copy; 2026 Likha Poha AI &middot; Made with ❤ in India
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

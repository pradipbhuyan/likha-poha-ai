/**
 * NoticeboardPricingTable.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Shared "Class Noticeboard" style plan-comparison table — the notebook-page
 * mockup style (grouped feature rows, ✓/✗ marks, plan-tab headers with
 * washi-tape badges). Used on:
 *   - LandingPage.jsx (public pricing section, dark theme)
 *   - SubscriptionPlansPage.jsx (student + parent views, app theme vars)
 *
 * Single source of truth for the PLANS/GROUPS data so all three surfaces
 * always show identical pricing/feature info.
 */
import { Fragment, useRef } from "react";
import "./NoticeboardPricingTable.css";

export const NOTICEBOARD_PLANS = [
  { key: "free_tier",        name: "Free Tier",        price: "₹0",     period: "forever", note: "Get started",  color: "#64748b" },
  { key: "starter",          name: "Premium",          price: "₹299",   period: "/ mo",     note: "Most popular", color: "#7c3aed", tag: "Popular" },
  { key: "family_premium",   name: "Family Premium",   price: "₹499",   period: "/ mo",     note: "Up to 2 kids", color: "#10b981", tag: "Best value" },
  { key: "exam_prep_center", name: "Exam Prep Center", price: "₹1,999", period: "/ yr",     note: "Gr 11–12 · JEE · NEET · CUET · SAT · IELTS · TOEFL", color: "#3b82f6", tag: "New" },
];

export const NOTICEBOARD_GROUPS = [
  { title: "Learning Core", rows: [
    ["CBSE Curriculum Coverage", "All subjects · all grades", "All subjects · all grades", "All subjects · all grades", "Grade 11–12 only"],
    ["AI-Powered Lessons", "Limited daily access", "Unlimited", "Unlimited", "Unlimited (Gr 11–12)"],
    ["Ask-a-Doubt (AI)", "5 / day", "Unlimited", "Unlimited", "Unlimited (Gr 11–12)"],
    ["Mock Tests", "5 / day", "Unlimited", "Unlimited", "Unlimited (Gr 11–12)"],
  ]},
  { title: "Exam Prep & Enrichment", rows: [
    ["Exemplar Research (Science & Maths)", false, true, true, true],
    ["Formula & Concepts Library", false, true, true, true],
    ["10 Years of Board Papers, with Answers", false, true, true, true],
    ["Learn More Video Library", true, true, true, true],
  ]},
  { title: "Competitive & Global Exams (Exam Prep Center)", rows: [
    ["JEE — Study Plan + Test Simulation", false, false, false, "Included"],
    ["NEET — Study Plan + Test Simulation", false, false, false, "Included"],
    ["CUET — Study Plan + Test Simulation", false, false, false, "Included"],
    ["SAT — Study Plan + Test Simulation", false, false, false, "Included"],
    ["IELTS — Study Plan + Test Simulation", false, false, false, "Included"],
    ["TOEFL — Study Plan + Test Simulation", false, false, false, "Included"],
  ]},
  { title: "Family & Parents", rows: [
    ["Child Profiles", "1", "1", "2", "1"],
    ["Parent Dashboard", "Basic", "Full + alerts", "Full + analytics", "Full + analytics"],
    ["Family Learning Management", false, false, true, true],
  ]},
  { title: "Plan & Support", rows: [
    ["Priority Support", false, true, true, true],
    ["Billing", "Free forever", "₹299 / month", "₹499 / month", "₹1,999 / year"],
    ["Plan Duration", "—", "Monthly", "Monthly", "Annual (Gr 11–12)"],
  ]},
];

function renderCell(v) {
  if (v === true) return <span className="nbp-mark pass">✓</span>;
  if (v === false) return <span className="nbp-mark cross">✗</span>;
  const strong = /unlimited|all subjects|included/i.test(v);
  return <span className={"nbp-cell-text" + (strong ? " strong" : "")}>{v}</span>;
}

/**
 * @param {"dark"|"light"} theme - "dark" for the landing page (fixed dark
 *   palette), "light" for app pages that use CSS var theming (works in both
 *   light and dark mode automatically via var(--text) etc.)
 * @param {function(string):void} onChoosePlan - called with a plan key when
 *   a CTA button is clicked ("free_tier" | "starter" | "family_premium" | "exam_prep_center")
 * @param {boolean} showCta - whether to render the CTA button row (hidden for
 *   parent-linked/teacher read-only views where a different action exists)
 * @param {boolean} showFreeCta - whether to render the "Start Free" button
 *   (hidden where free_tier isn't a real selectable plan, e.g. Subscription page)
 * @param {Array} plans - plan-tab data, defaults to NOTICEBOARD_PLANS (student/parent
 *   plans). Pass a different set (e.g. a 2-column Free Trial vs Paid) to reuse this
 *   same notebook-style table for other audiences, such as the teacher comparison.
 * @param {Array} groups - grouped feature rows, defaults to NOTICEBOARD_GROUPS.
 * @param {import('react').ReactNode} footnote - overrides the default footnote text
 *   under the table (which references INR pricing/Family Premium specifics that only
 *   apply to the student/parent plans).
 */
export default function NoticeboardPricingTable({
  theme = "light",
  onChoosePlan,
  showCta = true,
  showFreeCta = true,
  plans = NOTICEBOARD_PLANS,
  groups = NOTICEBOARD_GROUPS,
  footnote,
}) {
  const scrollRef = useRef(null);
  const colRefs = useRef({});

  function jumpToPlan(key) {
    /** Mobile-only quick jump: scroll the horizontally-scrolling table so the tapped plan's column lands right after the sticky feature column. */
    const wrap = scrollRef.current;
    const col = colRefs.current[key];
    if (!wrap || !col) return;
    const stickyWidth = wrap.querySelector(".nbp-feature-head")?.offsetWidth || 0;
    wrap.scrollTo({ left: col.offsetLeft - stickyWidth, behavior: "smooth" });
  }

  return (
    <div className={"nbp-root nbp-theme-" + theme}>
      <div className="nbp-jump-row" role="tablist" aria-label="Jump to plan">
        {plans.map(p => (
          <button
            key={p.key}
            type="button"
            className="nbp-jump-chip"
            style={{ borderColor: p.color }}
            onClick={() => jumpToPlan(p.key)}
          >
            {p.name}
          </button>
        ))}
      </div>
      <div className="nbp-wrap" ref={scrollRef}>
        <table className="nbp-table">
          <colgroup><col className="nbp-feature-col" />{plans.map(p => <col key={p.key} />)}</colgroup>
          <thead>
            <tr>
              <th className="nbp-feature-head">What&rsquo;s included</th>
              {plans.map(p => (
                <th key={p.key} ref={(el) => { colRefs.current[p.key] = el; }}>
                  <div className="nbp-plan-tab" style={{ background: p.color + "22" }}>
                    {p.tag && <div className="nbp-washi" style={{ background: p.color }}>{p.tag}</div>}
                    <div className="nbp-plan-name">{p.name}</div>
                    <div className="nbp-plan-price">{p.price}<span> {p.period}</span></div>
                    <div className="nbp-plan-note">{p.note}</div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map(g => (
              <Fragment key={g.title}>
                <tr className="nbp-group-row"><td colSpan={plans.length + 1}>{g.title}</td></tr>
                {g.rows.map(([label, ...vals]) => (
                  <tr key={label} className="nbp-feature-row">
                    <td className="nbp-feature-label">{label}</td>
                    {vals.map((v, i) => <td key={i} className="nbp-cell">{renderCell(v)}</td>)}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="nbp-swipe-hint">&#8596; Swipe or tap a plan above to compare</p>
      <div className="nbp-footnote">
        <span>✓ marked present &nbsp;&nbsp; ✗ marked absent</span>
        {footnote !== undefined ? footnote : (
          <span>Prices in INR &middot; Family Premium fits 2 children &middot; Exam Prep Center (&#8377;1,999/yr) is a Grade 11&ndash;12 only add&#8209;on covering JEE, NEET, CUET, SAT, IELTS & TOEFL</span>
        )}
      </div>
      {showCta && (
        <div className="nbp-cta-row">
          {showFreeCta && (
            <button className="nbp-btn nbp-btn-outline" onClick={() => onChoosePlan?.("free_tier")}>Start Free</button>
          )}
          <button className="nbp-btn nbp-btn-fill" onClick={() => onChoosePlan?.("starter")}>Choose Premium</button>
          <button className="nbp-btn nbp-btn-outline" onClick={() => onChoosePlan?.("family_premium")}>Get Family Premium</button>
          <button className="nbp-btn nbp-btn-outline" onClick={() => onChoosePlan?.("exam_prep_center")}>Get Exam Prep Center</button>
        </div>
      )}
    </div>
  );
}

/**
 * PrincipalDashboardPage.jsx — Principal Command Center
 *
 * School-wide oversight for a principal: teacher/student rosters, free-vs
 * -paid tier tracking, and the school-level incentive program. Every write
 * action here either links/unlinks an *existing* account's school_id, or
 * requests a reward redemption — nothing here creates a login or changes a
 * student's/teacher's plan, role, or credentials. See
 * backend/app/routes/principal_dashboard.py for the enforced boundary.
 */
import { useEffect, useState } from "react";
import {
  School, Users, GraduationCap, TrendingUp, Award, Copy, Check,
  UserPlus, X, Lock,
} from "lucide-react";
import {
  getPrincipalSchool,
  getPrincipalDashboardSummary,
  listPrincipalTeachers,
  linkTeacherToSchool,
  unlinkTeacherFromSchool,
  listPrincipalStudents,
  linkStudentToSchool,
  unlinkStudentFromSchool,
  getPrincipalIncentives,
  redeemPrincipalReward,
} from "../api/principalDashboard";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "teachers", label: "Teachers" },
  { key: "students", label: "Students" },
  { key: "incentives", label: "Incentives & Rewards" },
];

const TIER_LABELS = { bronze: "Bronze", silver: "Silver", gold: "Gold", platinum: "Platinum" };

const card = (extra) => ({
  background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)",
  borderRadius: 14, padding: "16px 18px", marginBottom: 16, ...(extra || {}),
});
const inputStyle = {
  padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border,#e5e7eb)",
  fontFamily: "inherit", fontSize: ".85rem", background: "var(--surface2,#f8fafc)",
  color: "var(--text,#1e293b)", flex: 1,
};
const btnPrimary = {
  padding: "8px 16px", borderRadius: 8, border: "none", background: "#6366f1",
  color: "#fff", fontFamily: "inherit", fontSize: ".82rem", fontWeight: 700, cursor: "pointer",
};
const btnGhost = {
  padding: "6px 12px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)",
  background: "var(--panel,#fff)", fontFamily: "inherit", fontSize: ".76rem",
  cursor: "pointer", color: "var(--text,#374151)",
};
const thStyle = {
  textAlign: "left", fontSize: ".7rem", textTransform: "uppercase", letterSpacing: ".04em",
  color: "var(--text-muted,#8288a0)", fontWeight: 700, padding: "0 10px 8px", borderBottom: "1px solid var(--border,#e5e7eb)",
};
const tdStyle = { padding: "10px", borderBottom: "1px solid var(--border-soft,#edeff4)", fontSize: ".85rem" };

function pill(bg, color, text) {
  return (
    <span style={{ background: bg, color, borderRadius: 999, padding: "3px 10px", fontSize: ".72rem", fontWeight: 700 }}>
      {text}
    </span>
  );
}

export default function PrincipalDashboardPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [school, setSchool] = useState(null);
  const [summary, setSummary] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [students, setStudents] = useState([]);
  const [studentTierFilter, setStudentTierFilter] = useState("");
  const [incentives, setIncentives] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [linkTeacherEmail, setLinkTeacherEmail] = useState("");
  const [linkStudentEmail, setLinkStudentEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  useEffect(() => {
    loadEverything();
  }, []);

  useEffect(() => {
    if (activeTab === "students") loadStudents(studentTierFilter);
  }, [studentTierFilter, activeTab]);

  async function loadEverything() {
    setLoading(true);
    setError("");
    try {
      const [schoolRes, summaryRes, teachersRes, studentsRes, incentivesRes] = await Promise.all([
        getPrincipalSchool(),
        getPrincipalDashboardSummary(),
        listPrincipalTeachers(),
        listPrincipalStudents(),
        getPrincipalIncentives(),
      ]);
      setSchool(schoolRes.school);
      setSummary(summaryRes);
      setTeachers(teachersRes.teachers || []);
      setStudents(studentsRes.students || []);
      setIncentives(incentivesRes);
    } catch (err) {
      setError(err.message || "We couldn't load your school dashboard.");
    } finally {
      setLoading(false);
    }
  }

  async function loadStudents(tier) {
    try {
      const res = await listPrincipalStudents(tier);
      setStudents(res.students || []);
    } catch (err) {
      setError(err.message || "We couldn't load the student roster.");
    }
  }

  async function refreshSummaryAndIncentives() {
    try {
      const [summaryRes, incentivesRes] = await Promise.all([
        getPrincipalDashboardSummary(),
        getPrincipalIncentives(),
      ]);
      setSummary(summaryRes);
      setIncentives(incentivesRes);
    } catch {
      // Non-critical — the acted-on list already reflects the change.
    }
  }

  async function handleLinkTeacher(e) {
    e.preventDefault();
    if (!linkTeacherEmail.trim()) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await linkTeacherToSchool(linkTeacherEmail.trim());
      setLinkTeacherEmail("");
      setMessage("Teacher linked to your school.");
      const res = await listPrincipalTeachers();
      setTeachers(res.teachers || []);
      refreshSummaryAndIncentives();
    } catch (err) {
      setError(err.message || "Couldn't find a teacher account with that email.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnlinkTeacher(teacherId) {
    setBusy(true);
    try {
      await unlinkTeacherFromSchool(teacherId);
      setTeachers((prev) => prev.filter((t) => t.id !== teacherId));
      refreshSummaryAndIncentives();
    } catch (err) {
      setError(err.message || "Couldn't remove that teacher.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLinkStudent(e) {
    e.preventDefault();
    if (!linkStudentEmail.trim()) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await linkStudentToSchool(linkStudentEmail.trim());
      setLinkStudentEmail("");
      setMessage("Student linked to your school.");
      await loadStudents(studentTierFilter);
      refreshSummaryAndIncentives();
    } catch (err) {
      setError(err.message || "Couldn't find a student account with that email.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnlinkStudent(studentId) {
    setBusy(true);
    try {
      await unlinkStudentFromSchool(studentId);
      setStudents((prev) => prev.filter((s) => s.id !== studentId));
      refreshSummaryAndIncentives();
    } catch (err) {
      setError(err.message || "Couldn't remove that student.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRedeem(rewardKey) {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await redeemPrincipalReward(rewardKey);
      setMessage("Reward requested — our team will follow up to fulfill it.");
      const res = await getPrincipalIncentives();
      setIncentives(res);
    } catch (err) {
      setError(err.message || "That reward isn't unlocked yet.");
    } finally {
      setBusy(false);
    }
  }

  function copyCode() {
    if (!school?.school_code) return;
    navigator.clipboard?.writeText(school.school_code).then(() => {
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 1500);
    });
  }

  if (loading) return <p style={{ padding: 24 }}>Loading your school dashboard…</p>;

  const unlockedKeys = new Set((incentives?.unlocked_rewards || []).map((r) => r.key));

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <p className="eyebrow">Principal Command Center</p>
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <School size={22} /> {school?.name || "Your School"}
            </h2>
            <p>Teachers, students, free-vs-paid tracking, and your school's incentive tier — all in one place.</p>
          </div>
          {school?.school_code && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--surface2,#f8fafc)", border: "1px dashed var(--border,#e5e7eb)", borderRadius: 9, padding: "8px 10px" }}>
              <div>
                <div style={{ fontSize: ".68rem", color: "var(--text-muted,#8288a0)" }}>School code</div>
                <div style={{ fontFamily: "monospace", fontWeight: 700, fontSize: ".95rem" }}>{school.school_code}</div>
              </div>
              <button type="button" style={btnGhost} onClick={copyCode} title="Copy code">
                {codeCopied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
          )}
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      {/* Tab strip */}
      <div style={{ display: "flex", gap: 4, background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: 4, marginBottom: 16, flexWrap: "wrap" }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: "1 1 auto", padding: "8px 14px", borderRadius: 8, border: "none",
              fontWeight: 700, fontSize: ".82rem", cursor: "pointer",
              background: activeTab === tab.key ? "rgba(99,102,241,.12)" : "transparent",
              color: activeTab === tab.key ? "#6366f1" : "var(--text-muted,#565b73)",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && summary && (
        <>
          <section className="premium-grid premium-grid-4 premium-parent-stats">
            <div className="premium-card">
              <div className="dashboard-stat-icon purple"><GraduationCap size={22} /></div>
              <h3>{summary.teacher_count}</h3>
              <p>Teachers</p>
            </div>
            <div className="premium-card">
              <div className="dashboard-stat-icon blue"><Users size={22} /></div>
              <h3>{summary.student_count}</h3>
              <p>Total Students</p>
            </div>
            <div className="premium-card">
              <div className="dashboard-stat-icon green"><TrendingUp size={22} /></div>
              <h3>{summary.paid_student_count}</h3>
              <p>Paid Students</p>
            </div>
            <div className="premium-card">
              <div className="dashboard-stat-icon red"><Award size={22} /></div>
              <h3>{summary.conversion_rate}%</h3>
              <p>Conversion Rate</p>
            </div>
          </section>

          <div className="premium-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
              <strong>Free vs. paid</strong>
              <span style={{ fontSize: ".8rem", color: "var(--text-muted,#8288a0)" }}>{summary.student_count} students total</span>
            </div>
            <div style={{ height: 20, borderRadius: 6, overflow: "hidden", display: "flex", background: "var(--surface2,#f8fafc)" }}>
              <div style={{ width: `${summary.student_count ? (summary.free_student_count / summary.student_count) * 100 : 0}%`, background: "#6366f1" }} />
              <div style={{ width: `${summary.student_count ? (summary.paid_student_count / summary.student_count) * 100 : 0}%`, background: "#10b981", borderLeft: "2px solid var(--panel,#fff)" }} />
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: ".8rem", color: "var(--text-muted,#565b73)" }}>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 3, background: "#6366f1", marginRight: 6 }} />Free — {summary.free_student_count}</span>
              <span><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 3, background: "#10b981", marginRight: 6 }} />Paid — {summary.paid_student_count}</span>
            </div>

            {summary.next_tier && (
              <div style={{ marginTop: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".8rem", marginBottom: 6 }}>
                  <strong>Reward tier progress — {TIER_LABELS[summary.tier]} → {TIER_LABELS[summary.next_tier.tier]}</strong>
                </div>
                <div style={{ height: 10, borderRadius: 6, background: "rgba(245,158,11,.15)", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%", background: "#f59e0b", borderRadius: 6,
                      width: `${Math.min(100, ((summary.paid_student_count) / summary.next_tier.threshold) * 100)}%`,
                    }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".76rem", color: "var(--text-muted,#8288a0)", marginTop: 6 }}>
                  <span>{summary.paid_student_count} of {summary.next_tier.threshold} paid students</span>
                  <span>{summary.next_tier.remaining} more for {TIER_LABELS[summary.next_tier.tier]}</span>
                </div>
              </div>
            )}
          </div>

          <div className="callout-note" style={{ ...card(), background: "rgba(99,102,241,.06)", border: "1px solid rgba(99,102,241,.2)", fontSize: ".8rem", color: "var(--text-muted,#565b73)" }}>
            You see enrollment, tiers, and activity summaries only. Individual doubt chats and lesson activity stay private to each student and their teacher.
          </div>
        </>
      )}

      {activeTab === "teachers" && (
        <div className="premium-card">
          <form onSubmit={handleLinkTeacher} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input
              type="email"
              placeholder="Link an existing teacher by email"
              value={linkTeacherEmail}
              onChange={(e) => setLinkTeacherEmail(e.target.value)}
              style={inputStyle}
            />
            <button type="submit" disabled={busy} style={btnPrimary}>
              <UserPlus size={14} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Link teacher
            </button>
          </form>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Teacher</th>
                  <th style={thStyle}>Email</th>
                  <th style={thStyle}>Assigned students</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle} />
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id}>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{t.username}</td>
                    <td style={tdStyle}>{t.email}</td>
                    <td style={tdStyle}>{t.assigned_students}</td>
                    <td style={tdStyle}>{pill("rgba(16,185,129,.12)", "#10b981", t.account_status || "active")}</td>
                    <td style={tdStyle}>
                      <button type="button" style={btnGhost} disabled={busy} onClick={() => handleUnlinkTeacher(t.id)}>
                        <X size={13} style={{ verticalAlign: "middle", marginRight: 4 }} />Remove
                      </button>
                    </td>
                  </tr>
                ))}
                {teachers.length === 0 && (
                  <tr><td style={tdStyle} colSpan={5}>No teachers linked to your school yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "students" && (
        <div className="premium-card">
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {[{ key: "", label: "All" }, { key: "free", label: "Free" }, { key: "paid", label: "Paid" }].map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setStudentTierFilter(f.key)}
                style={{
                  ...btnGhost,
                  background: studentTierFilter === f.key ? "#6366f1" : "var(--panel,#fff)",
                  color: studentTierFilter === f.key ? "#fff" : "var(--text,#374151)",
                  borderColor: studentTierFilter === f.key ? "#6366f1" : "var(--border,#e5e7eb)",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleLinkStudent} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input
              type="email"
              placeholder="Link an existing student by email"
              value={linkStudentEmail}
              onChange={(e) => setLinkStudentEmail(e.target.value)}
              style={inputStyle}
            />
            <button type="submit" disabled={busy} style={btnPrimary}>
              <UserPlus size={14} style={{ verticalAlign: "middle", marginRight: 6 }} />
              Link student
            </button>
          </form>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Student</th>
                  <th style={thStyle}>Grade</th>
                  <th style={thStyle}>Tier</th>
                  <th style={thStyle}>Last active</th>
                  <th style={thStyle} />
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{s.username}</td>
                    <td style={tdStyle}>{s.grade}</td>
                    <td style={tdStyle}>
                      {s.tier === "paid"
                        ? pill("rgba(16,185,129,.12)", "#10b981", `Paid${s.subscription_plan ? ` · ${s.subscription_plan}` : ""}`)
                        : pill("var(--surface2,#f8fafc)", "var(--text-muted,#565b73)", "Free")}
                    </td>
                    <td style={tdStyle}>{s.last_active_date || "—"}</td>
                    <td style={tdStyle}>
                      <button type="button" style={btnGhost} disabled={busy} onClick={() => handleUnlinkStudent(s.id)}>
                        <X size={13} style={{ verticalAlign: "middle", marginRight: 4 }} />Remove
                      </button>
                    </td>
                  </tr>
                ))}
                {students.length === 0 && (
                  <tr><td style={tdStyle} colSpan={5}>No students linked to your school yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: 14, fontSize: ".78rem", color: "var(--text-muted,#8288a0)" }}>
            Tier is shown so you can direct support to where it's needed. Linking a student only adds them to this roster — it never changes their login, plan, or what they can do. Chat/doubt content stays private regardless of tier.
          </div>
        </div>
      )}

      {activeTab === "incentives" && incentives && (
        <>
          <div className="premium-card">
            <div className="premium-header" style={{ marginBottom: 12 }}>
              <h3>{school?.name} is on the {TIER_LABELS[incentives.tier]} tier</h3>
              <p>Rewards are earned by the school, for the school — not a personal payout to any one person.</p>
            </div>

            {incentives.next_tier && (
              <>
                <div style={{ height: 10, borderRadius: 6, background: "rgba(245,158,11,.15)", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%", background: "#f59e0b", borderRadius: 6,
                      width: `${Math.min(100, (incentives.paid_student_count / incentives.next_tier.threshold) * 100)}%`,
                    }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".76rem", color: "var(--text-muted,#8288a0)", marginTop: 6 }}>
                  <span>{incentives.paid_student_count} / {incentives.next_tier.threshold} paid students to reach {TIER_LABELS[incentives.next_tier.tier]}</span>
                  <span>{incentives.next_tier.remaining} to go</span>
                </div>
              </>
            )}
            {!incentives.next_tier && (
              <div style={{ fontSize: ".85rem", color: "var(--text-muted,#565b73)" }}>Your school has reached the top tier — Platinum.</div>
            )}
          </div>

          <div className="premium-card">
            <div className="premium-header" style={{ marginBottom: 12 }}>
              <h3>Reward catalog</h3>
              <p>Unlocked at your tier, plus what's next</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
              {Object.entries(incentives.catalog || {}).flatMap(([tier, rewards]) =>
                rewards.map((reward) => {
                  const unlocked = unlockedKeys.has(reward.key);
                  return (
                    <div key={reward.key} style={{ ...card({ marginBottom: 0, opacity: unlocked ? 1 : 0.6 }) }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        {pill(
                          unlocked ? "rgba(16,185,129,.12)" : "var(--surface2,#f8fafc)",
                          unlocked ? "#10b981" : "var(--text-muted,#565b73)",
                          TIER_LABELS[tier],
                        )}
                        {!unlocked && <Lock size={13} color="var(--text-muted,#8288a0)" />}
                      </div>
                      <div style={{ fontWeight: 700, fontSize: ".85rem", marginBottom: 4 }}>{reward.label}</div>
                      <div style={{ fontSize: ".78rem", color: "var(--text-muted,#8288a0)", marginBottom: 10 }}>{reward.description}</div>
                      <button
                        type="button"
                        disabled={!unlocked || busy}
                        onClick={() => handleRedeem(reward.key)}
                        style={{ ...btnGhost, width: "100%", opacity: unlocked ? 1 : 0.5, cursor: unlocked ? "pointer" : "not-allowed" }}
                      >
                        {unlocked ? "Redeem" : "Locked"}
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="premium-card">
            <div className="premium-header" style={{ marginBottom: 12 }}>
              <h3>Redemption history</h3>
            </div>
            {(incentives.redemption_history || []).length === 0 && (
              <p style={{ fontSize: ".85rem", color: "var(--text-muted,#8288a0)" }}>No rewards redeemed yet.</p>
            )}
            {(incentives.redemption_history || []).map((r) => (
              <div key={r.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border-soft,#edeff4)", fontSize: ".82rem" }}>
                <span>{r.reward_label}</span>
                {pill(r.status === "fulfilled" ? "rgba(16,185,129,.12)" : "rgba(245,158,11,.12)", r.status === "fulfilled" ? "#10b981" : "#f59e0b", r.status)}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";

import { getUserHistory } from "../api/analytics";
import { getUsageSummary } from "../api/usage";

import {
  getFamily,
  createStudent,
  inviteParent,
  getWeakAreaAlerts,
} from "../api/parentDashboard";

import { BarChart3, ClipboardList, Target, Trophy } from "lucide-react";

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

function ParentDashboardPage() {
  /** Parent view for managing family members and monitoring child progress and usage. */
  const [familyId, setFamilyId] = useState(null);
  const [parents, setParents] = useState([]);
  const [children, setChildren] = useState([]);
  const [selectedChild, setSelectedChild] = useState(null);

  const [history, setHistory] = useState([]);
  const [usage, setUsage] = useState(null);
  const [weakAreaAlerts, setWeakAreaAlerts] = useState([]);

  const [familyLoading, setFamilyLoading] = useState(true);
  const [childLoading, setChildLoading] = useState(false);

  const [showAddChild, setShowAddChild] = useState(false);
  const [showInviteParent, setShowInviteParent] = useState(false);

  const [studentName, setStudentName] = useState("");
  const [studentEmail, setStudentEmail] = useState("");
  const [studentPassword, setStudentPassword] = useState("");
  const [studentGrade, setStudentGrade] = useState("");
  const [creatingStudent, setCreatingStudent] = useState(false);

  const [parentName, setParentName] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [parentPassword, setParentPassword] = useState("");
  const [invitingParent, setInvitingParent] = useState(false);

  async function loadFamily() {
    /** Load parent and child records, preserving the currently selected child when possible. */
    setFamilyLoading(true);

    try {
      const result = await getFamily();

      const loadedParents = result.parents || [];
      const loadedChildren = result.children || [];

      setFamilyId(result.family_id);
      setParents(loadedParents);
      setChildren(loadedChildren);

      if (loadedChildren.length > 0) {
        setSelectedChild((current) => {
          if (!current) return loadedChildren[0];

          return (
            loadedChildren.find((child) => child.id === current.id) ||
            loadedChildren[0]
          );
        });
      } else {
        setSelectedChild(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setFamilyLoading(false);
    }
  }

  useEffect(() => {
    loadFamily();
  }, []);

  useEffect(() => {
    async function loadChildData() {
      /** Refresh analytics, usage, and weak-area alerts for the selected child. */
      if (!selectedChild) {
        setHistory([]);
        setUsage(null);
        setWeakAreaAlerts([]);
        return;
      }

      setChildLoading(true);

      try {
        const username = selectedChild.username;

        const historyData = await getUserHistory(username);
        const usageData = await getUsageSummary(username);
        const alertData = await getWeakAreaAlerts(selectedChild.id);

        setHistory(historyData.history || []);
        setUsage(usageData);
        setWeakAreaAlerts(alertData.alerts || []);

      } catch (err) {
        console.error(err);
      } finally {
        setChildLoading(false);
      }
    }

    loadChildData();
  }, [selectedChild]);

  async function handleCreateStudent(e) {
    /** Create a child account under the current family and refresh the dashboard. */
    e.preventDefault();

    setCreatingStudent(true);

    try {
      if (!studentGrade) {
        alert("Please select your child's class before creating the account.");
        setCreatingStudent(false);
        return;
      }

      await createStudent({
        username: studentName,
        email: studentEmail,
        password: studentPassword,
        grade: studentGrade,
      });

      setStudentName("");
      setStudentEmail("");
      setStudentPassword("");
      setStudentGrade("");
      setShowAddChild(false);

      await loadFamily();

      alert("Student created successfully.");
    } catch (err) {
      console.error(err);
      alert(err.message || "Unable to create student.");
    } finally {
      setCreatingStudent(false);
    }
  }

  async function handleInviteParent(e) {
    /** Add another parent login to the same family and reload the family roster. */
    e.preventDefault();

    setInvitingParent(true);

    try {
      await inviteParent({
        username: parentName,
        email: parentEmail,
        password: parentPassword,
      });

      setParentName("");
      setParentEmail("");
      setParentPassword("");
      setShowInviteParent(false);

      await loadFamily();

      alert("Parent invited successfully.");
    } catch (err) {
      console.error(err);
      alert(err.message || "Unable to invite parent.");
    } finally {
      setInvitingParent(false);
    }
  }

  if (familyLoading) {
    return <p>Loading family dashboard...</p>;
  }

  const childName = selectedChild?.username || "Student";

  const totalTests = history.length;
  const scores = history.map((item) => Number(item.percentage || 0));

  const averageScore = scores.length
    ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length)
    : 0;

  const bestScore = scores.length ? Math.max(...scores) : 0;
  const latestScore = scores.length ? scores[scores.length - 1] : 0;

  const scoreTrend = history.map((item, index) => ({
    name: `Test ${index + 1}`,
    score: Number(item.percentage || 0),
  }));

  const subjectMap = {};

  history.forEach((item) => {
    const subject = item.subject || "Unknown";
    const score = Number(item.percentage || 0);

    if (!subjectMap[subject]) {
      subjectMap[subject] = { total: 0, count: 0 };
    }

    subjectMap[subject].total += score;
    subjectMap[subject].count += 1;
  });

  const subjectPerformance = Object.entries(subjectMap).map(
    ([subject, value]) => ({
      subject,
      average: Math.round(value.total / value.count),
    })
  );

  const parentInsight =
    latestScore >= 85
      ? `${childName} is performing strongly. Encourage harder practice and Olympiad-style questions.`
      : latestScore >= 60
      ? `${childName} is progressing well. Weekly revision and mistake review will help improve consistency.`
      : `${childName} may need guided revision. Start with weak chapters, then use short tests to rebuild confidence.`;

  return (
    <div className="parent-dashboard-page premium-page premium-parent-page">
      <section className="premium-section parent-family-hub">
        <div className="parent-family-copy">
          <p className="eyebrow">Family Hub</p>

          <h2>Family Learning Center</h2>

          <p>
            Manage parents, children, progress, test performance
            from one clean dashboard.
          </p>

          <div className="family-summary-row">
            <span>
              {parents.length} Parent{parents.length === 1 ? "" : "s"}
            </span>
            <span>
              {children.length} Child{children.length === 1 ? "" : "ren"}
            </span>
          </div>

          <div className="family-action-row">
            <button
              className="primary-btn"
              onClick={() => setShowAddChild(true)}
              disabled={children.length >= 2}
            >
              {children.length >= 2 ? "Child Limit Reached" : "+ Add Child"}
            </button>

            <button
              className="secondary-btn"
              onClick={() => setShowInviteParent(true)}
              disabled={parents.length >= 2}
            >
              {parents.length >= 2 ? "Parent Limit Reached" : "+ Invite Parent"}
            </button>
          </div>
        </div>

        <div className="family-member-panel">
          <div>
            <h3>Parents</h3>

            <div className="family-card-grid">
              {parents.length === 0 ? (
                <p className="muted">No parents found.</p>
              ) : (
                parents.map((parent) => (
                  <div key={parent.id} className="family-person-card parent">
                    <div className="family-avatar">
                      {(parent.username ||
                        parent.email ||
                        "P")[0].toUpperCase()}
                    </div>

                    <div>
                      <strong>{parent.username || "Parent"}</strong>
                      <small>Parent</small>
                      <small>{parent.email}</small>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div>
            <h3>Children</h3>

            <div className="family-card-grid">
              {children.length === 0 ? (
                <div className="family-empty-card">
                  <strong>No children yet</strong>
                  <small>Create your first student account.</small>
                </div>
              ) : (
                children.map((child) => (
                  <button
                    key={child.id}
                    className={
                      selectedChild?.id === child.id
                        ? "family-person-card child selected"
                        : "family-person-card child"
                    }
                    onClick={() => setSelectedChild(child)}
                  >
                    <div className="family-avatar child-avatar">
                      {(child.username || child.email || "S")[0].toUpperCase()}
                    </div>

                    <div>
                      <strong>{child.username || "Student"}</strong>
                      <small>Student</small>
                      <small>{child.email}</small>
                    </div>

                    {selectedChild?.id === child.id && (
                      <em className="selected-child-badge">Viewing</em>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      {!selectedChild ? (
        <section className="premium-section premium-parent-empty">
          <h3>No linked students found</h3>
          <p>Create a student account to unlock progress insights.</p>
          <button
            className="primary-btn"
            onClick={() => setShowAddChild(true)}
            disabled={children.length >= 2}
          >
            {children.length >= 2 ? "Child Limit Reached" : "+ Add Child"}
          </button>
        </section>
      ) : childLoading ? (
        <p>Loading child analytics...</p>
      ) : (
        <>
          <section className="premium-section selected-child-overview">
            <div className="premium-header">
              <p className="eyebrow">Selected Child</p>
              <h2>{childName}&apos;s Learning Overview</h2>
              <p>
                Track learning progress, test performance, and
                suggested next steps.
              </p>
            </div>

            <div className="premium-parent-insight-card">
              <span>💡</span>

              <div>
                <strong>Parent Suggestion</strong>
                <p>{parentInsight}</p>
              </div>
            </div>
          </section>

          {weakAreaAlerts.length > 0 && (
            <section className="premium-section">
              <div className="premium-header">
                <h3>⚠️ Learning Alerts</h3>
                <p>
                  These topics were continued without full mastery and should be
                  revised.
                </p>
              </div>

              <div className="premium-parent-activity-list">
                {weakAreaAlerts.slice(0, 5).map((alert) => (
                  <div key={alert.id} className="premium-parent-activity-row">
                    <div>
                      <strong>{alert.chapter}</strong>
                      <p>
                        {alert.subject} • {alert.step_title}
                      </p>
                      <small>
                        Attempts: {alert.attempts} • Best Score:{" "}
                        {alert.best_score}/10
                      </small>
                    </div>

                    <span>Needs Revision</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="premium-grid premium-grid-4 premium-parent-stats">
            <div className="premium-card premium-glow-card glow-blue">
              <div className="dashboard-stat-icon blue">
                <ClipboardList size={28} strokeWidth={2.4} />
              </div>
              <h3>{totalTests}</h3>
              <p>Mock tests completed</p>
            </div>

            <div className="premium-card premium-glow-card glow-green">
              <div className="dashboard-stat-icon green">
                <BarChart3 size={28} strokeWidth={2.4} />
              </div>
              <h3>{averageScore}%</h3>
              <p>Average score</p>
            </div>

            <div className="premium-card premium-glow-card glow-purple">
              <div className="dashboard-stat-icon purple">
                <Trophy size={28} strokeWidth={2.4} />
              </div>
              <h3>{bestScore}%</h3>
              <p>Best score</p>
            </div>

            <div className="premium-card premium-glow-card glow-red">
              <div className="dashboard-stat-icon red">
                <Target size={28} strokeWidth={2.4} />
              </div>
              <h3>{latestScore}%</h3>
              <p>Latest score</p>
            </div>
          </section>

          <section className="analytics-chart-grid premium-parent-chart-grid">
            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📈 Score Trend</h3>
                  <p>Student performance over time.</p>
                </div>
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={scoreTrend}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#3b82f6"
                      strokeWidth={3}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="dashboard-chart-card premium-card premium-chart-card">
              <div className="section-heading-row">
                <div>
                  <h3>📚 Subject Performance</h3>
                  <p>Average score by subject.</p>
                </div>
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={subjectPerformance}>
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis dataKey="subject" stroke="#94a3b8" />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" />
                    <Tooltip />
                    <Bar
                      dataKey="average"
                      fill="#3b82f6"
                      radius={[10, 10, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="dashboard-bottom-grid premium-parent-bottom-grid">
            <div className="premium-section premium-parent-activity">
              <div className="premium-header">
                <h3>🕘 Recent Test Activity</h3>
                <p>Latest mock tests completed.</p>
              </div>

              {history.length === 0 ? (
                <div className="premium-parent-empty">
                  <h3>No test history yet</h3>
                  <p>
                    Ask the student to complete a mock test to unlock insights.
                  </p>
                </div>
              ) : (
                <div className="premium-parent-activity-list">
                  {[...history]
                    .reverse()
                    .slice(0, 5)
                    .map((item, index) => (
                      <div key={index} className="premium-parent-activity-row">
                        <div>
                          <strong>{item.subject}</strong>
                          <p>{item.chapter || item.mockType}</p>
                        </div>

                        <span>{item.percentage}%</span>
                      </div>
                    ))}
                </div>
              )}
            </div>

          </section>
        </>
      )}

      {showAddChild && (
        <div className="modal-backdrop">
          <div className="premium-modal">
            <button
              className="modal-close"
              onClick={() => setShowAddChild(false)}
            >
              ×
            </button>

            <h3>Add Child</h3>
            <p>Create a student login under this family.</p>

            <form onSubmit={handleCreateStudent}>
              <input
                type="text"
                placeholder="Student Name"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                required
              />

              <input
                type="email"
                placeholder="Student Email (optional)"
                value={studentEmail}
                onChange={(e) => setStudentEmail(e.target.value)}
              />
              <small style={{ color: "#888", fontSize: "0.78rem", marginTop: -6 }}>
                Leave blank if the student does not have an email — they can still log in with their username and password.
              </small>

              <label style={{ display:"block", marginBottom:4, fontSize:".85rem", fontWeight:600 }}>
                Child's Class *
              </label>
              <select
                value={studentGrade}
                onChange={(e) => setStudentGrade(e.target.value)}
                required
                style={{ marginBottom:12 }}
              >
                <option value="">— Select class —</option>
                {/* Platform supports Grade 5–10. Add new grades here when platform expands. */}
                {["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"].map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>

              <input
                type="password"
                placeholder="Temporary Password"
                value={studentPassword}
                onChange={(e) => setStudentPassword(e.target.value)}
                required
              />

              <button
                className="primary-btn"
                type="submit"
                disabled={creatingStudent || children.length >= 2}
              >
                {creatingStudent ? "Creating..." : "Create Student"}
              </button>
            </form>
          </div>
        </div>
      )}

      {showInviteParent && (
        <div className="modal-backdrop">
          <div className="premium-modal">
            <button
              className="modal-close"
              onClick={() => setShowInviteParent(false)}
            >
              ×
            </button>

            <h3>Invite Parent</h3>
            <p>Add another parent to the same family.</p>

            <form onSubmit={handleInviteParent}>
              <input
                type="text"
                placeholder="Parent Name"
                value={parentName}
                onChange={(e) => setParentName(e.target.value)}
                required
              />

              <input
                type="email"
                placeholder="Parent Email"
                value={parentEmail}
                onChange={(e) => setParentEmail(e.target.value)}
                required
              />

              <input
                type="password"
                placeholder="Temporary Password"
                value={parentPassword}
                onChange={(e) => setParentPassword(e.target.value)}
                required
              />

              <button
                className="primary-btn"
                type="submit"
                disabled={invitingParent || parents.length >= 2}
              >
                {invitingParent ? "Inviting..." : "Invite Parent"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default ParentDashboardPage;

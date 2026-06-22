import React, { useEffect, useState } from "react";
import { GRADE_11_12_STREAMS, getSubjectsForStream, isStreamGrade } from "../utils/streamSubjects";

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

/** Desktop webcam capture component using getUserMedia */
function WebcamCaptureModal({ onCapture, onClose }) {
  const videoRef = React.useRef(null);
  const canvasRef = React.useRef(null);
  const [stream, setStream] = React.useState(null);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then(s => {
        setStream(s);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError("Camera not available or permission denied."));
    return () => {
      // Stop camera when modal closes
      setStream(prev => { prev?.getTracks().forEach(t => t.stop()); return null; });
    };
  }, []);

  function capture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    stream?.getTracks().forEach(t => t.stop());
    onCapture(dataUrl);
  }

  return (
    <div className="modal-backdrop" style={{ zIndex: 1100 }}>
      <div className="premium-modal" style={{ maxWidth: 480, textAlign: "center" }}>
        <button className="modal-close" onClick={() => { stream?.getTracks().forEach(t => t.stop()); onClose(); }}>×</button>
        <h3 style={{ marginBottom: 12 }}>📸 Take a Photo</h3>
        {error ? (
          <div className="error-box">{error}</div>
        ) : (
          <>
            <video ref={videoRef} autoPlay playsInline muted
              style={{ width: "100%", borderRadius: 12, background: "#111827", maxHeight: 320 }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <button className="primary-btn" onClick={capture} style={{ marginTop: 14, width: "100%" }}>
              📷 Capture Photo
            </button>
          </>
        )}
        <p style={{ fontSize: ".75rem", color: "var(--muted)", marginTop: 10 }}>
          Browser will ask for camera permission. Allow it to take the photo.
        </p>
      </div>
    </div>
  );
}

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
  const [studentStream, setStudentStream] = useState("");
  const [studentAvatar, setStudentAvatar] = useState(""); // emoji key or data: URL
  const [showWebcam, setShowWebcam] = useState(false);
  const [creatingStudent, setCreatingStudent] = useState(false);
  const [createStudentError, setCreateStudentError] = useState("");

  // Free preset avatars — boy, girl, and gender-neutral options
  const PRESET_AVATARS = [
    { key:"boy1",   emoji:"👦" },
    { key:"boy2",   emoji:"🧒" },
    { key:"boy3",   emoji:"👨‍🎓" },
    { key:"girl1",  emoji:"👧" },
    { key:"girl2",  emoji:"🧒‍♀️" },
    { key:"girl3",  emoji:"👩‍🎓" },
    { key:"star",   emoji:"⭐" },
    { key:"rocket", emoji:"🚀" },
    { key:"book",   emoji:"📚" },
    { key:"brain",  emoji:"🧠" },
  ];
  // Stores credentials after child creation to show the "What to do next" card
  const [createdChildInfo, setCreatedChildInfo] = useState(null);

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
      setCreateStudentError("");
      if (!studentGrade) {
        setCreateStudentError("Please select your child's class before creating the account.");
        setCreatingStudent(false);
        return;
      }

      await createStudent({
        username: studentName,
        email: studentEmail,
        password: studentPassword,
        grade: studentGrade,
        avatar: studentAvatar || undefined,
        // For Grade 11/12: set cbse_subjects from stream so only stream subjects show
        cbse_subjects: (isStreamGrade(studentGrade) && studentStream)
          ? getSubjectsForStream(studentStream)
          : undefined,
      });

      // Save credentials for the "What to do next" card
      setCreatedChildInfo({
        username: studentName,
        email: studentEmail,
        password: studentPassword,
        grade: studentGrade,
        avatar: studentAvatar || "",
      });

      setStudentName("");
      setStudentEmail("");
      setStudentPassword("");
      setStudentGrade("");
      setStudentStream("");
      setStudentAvatar("");
      setShowAddChild(false);

      await loadFamily();
    } catch (err) {
      console.error(err);
      const msg = err.message || "Unable to create student.";
      const isAuthErr = msg.toLowerCase().includes("parent") ||
                        msg.toLowerCase().includes("access") ||
                        msg.toLowerCase().includes("auth") ||
                        msg.toLowerCase().includes("token") ||
                        msg.toLowerCase().includes("unauthorized") ||
                        msg.toLowerCase().includes("403") ||
                        msg.toLowerCase().includes("401");
      setCreateStudentError(
        isAuthErr
          ? "⚠️ Session expired or access issue detected.\n\nPlease log out and log back in to fix this. Your family data is safe."
          : msg
      );
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
                  <div key={child.id} style={{ display:"flex", flexDirection:"column", gap:6 }}>
                    <button
                      className={
                        selectedChild?.id === child.id
                          ? "family-person-card child selected"
                          : "family-person-card child"
                      }
                      onClick={() => setSelectedChild(child)}
                    >
                      <div className="family-avatar child-avatar" style={{
                        overflow: "hidden",
                        fontSize: child.avatar && child.avatar.startsWith("data:") ? 0
                                 : child.avatar ? "1.5rem" : undefined,
                        background: child.avatar ? "transparent" : undefined,
                      }}>
                        {child.avatar && child.avatar.startsWith("data:") ? (
                          <img src={child.avatar} alt={child.username} style={{ width:"100%", height:"100%", objectFit:"cover" }} />
                        ) : child.avatar ? (
                          PRESET_AVATARS.find(a => a.key === child.avatar)?.emoji || child.username?.[0]?.toUpperCase() || "S"
                        ) : (
                          (child.username || child.email || "S")[0].toUpperCase()
                        )}
                      </div>

                      <div>
                        <strong>{child.username || "Student"}</strong>
                        <small>Student</small>
                        <small>{child.email || child.username}</small>
                      </div>

                      {selectedChild?.id === child.id && (
                        <em className="selected-child-badge">Viewing</em>
                      )}
                    </button>
                    {/* Persistent sign-in-as-child link */}
                    {child.email && (
                      <a
                        href={`https://likhapoha.in/?u=${encodeURIComponent(child.email)}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:6, background:"rgba(99,102,241,.1)", border:"1px solid rgba(99,102,241,.3)", borderRadius:8, padding:"5px 10px", fontSize:".72rem", color:"#a5b4fc", fontWeight:600, textDecoration:"none", cursor:"pointer" }}>
                        🔑 Sign in as {child.username || "child"}
                      </a>
                    )}
                  </div>
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
            <div className="premium-card premium-glow-card glow-red">
              <div className="dashboard-stat-icon red">
                <Target size={28} strokeWidth={2.4} />
              </div>
              <h3>{latestScore}%</h3>
              <p>Latest score</p>
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

            <div className="premium-card premium-glow-card glow-blue">
              <div className="dashboard-stat-icon blue">
                <ClipboardList size={28} strokeWidth={2.4} />
              </div>
              <h3>{totalTests}</h3>
              <p>Mock tests completed</p>
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
          <div className="premium-modal" style={{ maxHeight: "90vh", overflowY: "auto", WebkitOverflowScrolling: "touch" }}>
            <button
              className="modal-close"
              onClick={() => setShowAddChild(false)}
            >
              ×
            </button>

            <h3>Add Child</h3>
            <p>Create a student login under this family.</p>

            <form onSubmit={handleCreateStudent}>
              {/* ── Avatar picker ── */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display:"block", fontSize:".85rem", fontWeight:600, marginBottom:8 }}>
                  Profile Picture <span style={{ color:"#64748b", fontWeight:400 }}>(optional)</span>
                </label>

                {/* Current avatar preview */}
                <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:12 }}>
                  <div style={{
                    width:60, height:60, borderRadius:"50%",
                    background:"rgba(99,102,241,.15)", border:"2px solid rgba(99,102,241,.3)",
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize: studentAvatar && studentAvatar.startsWith("data:") ? 0 : "2rem",
                    overflow:"hidden", flexShrink:0,
                  }}>
                    {studentAvatar && studentAvatar.startsWith("data:") ? (
                      <img src={studentAvatar} alt="avatar" style={{ width:"100%", height:"100%", objectFit:"cover" }} />
                    ) : studentAvatar ? (
                      PRESET_AVATARS.find(a => a.key === studentAvatar)?.emoji || "🧒"
                    ) : (
                      <span style={{ fontSize:"1.6rem", color:"#64748b" }}>👤</span>
                    )}
                  </div>
                  <div>
                    <p style={{ fontSize:".78rem", color:"#94a3b8", margin:0 }}>
                      {studentAvatar ? "Avatar selected ✓" : "No avatar chosen"}
                    </p>
                    {studentAvatar && (
                      <button type="button" onClick={() => setStudentAvatar("")}
                        style={{ background:"none", border:"none", color:"#f87171", fontSize:".72rem", cursor:"pointer", padding:0, marginTop:2 }}>
                        × Remove
                      </button>
                    )}
                  </div>
                </div>

                {/* Preset emoji avatars */}
                <p style={{ fontSize:".75rem", color:"#64748b", marginBottom:6, fontWeight:600 }}>Choose a preset avatar:</p>
                <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:12 }}>
                  {PRESET_AVATARS.map(av => (
                    <button
                      key={av.key}
                      type="button"
                      onClick={() => setStudentAvatar(av.key)}
                      style={{
                        width:44, height:44, borderRadius:"50%", border:`2px solid ${studentAvatar === av.key ? "#6366f1" : "rgba(99,102,241,.2)"}`,
                        background: studentAvatar === av.key ? "rgba(99,102,241,.2)" : "rgba(99,102,241,.06)",
                        fontSize:"1.5rem", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center",
                        transition:"all .15s",
                        boxShadow: studentAvatar === av.key ? "0 0 0 3px rgba(99,102,241,.35)" : "none",
                      }}
                      title={av.key}
                    >{av.emoji}</button>
                  ))}
                </div>

                {/* Upload / Camera */}
                <p style={{ fontSize:".75rem", color:"#64748b", marginBottom:6, fontWeight:600 }}>Or upload a photo:</p>
                <div style={{ display:"flex", gap:8 }}>
                  {/* Upload from gallery — always available */}
                  <label style={{
                    flex:1, display:"flex", alignItems:"center", justifyContent:"center", gap:6,
                    background:"rgba(99,102,241,.08)", border:"1px solid rgba(99,102,241,.2)",
                    borderRadius:8, padding:"8px 12px", cursor:"pointer", fontSize:".8rem", color:"#a5b4fc", fontWeight:600,
                  }}>
                    📁 Upload Photo
                    <input type="file" accept="image/*" style={{ display:"none" }}
                      onChange={e => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        const reader = new FileReader();
                        reader.onload = ev => setStudentAvatar(ev.target.result);
                        reader.readAsDataURL(file);
                      }} />
                  </label>

                  {/* Take Photo:
                      Mobile → no capture attr so OS shows camera chooser (front + back + gallery)
                      Desktop → open webcam modal via getUserMedia */}
                  {/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? (
                    <label style={{
                      flex:1, display:"flex", alignItems:"center", justifyContent:"center", gap:6,
                      background:"rgba(16,185,129,.08)", border:"1px solid rgba(16,185,129,.2)",
                      borderRadius:8, padding:"8px 12px", cursor:"pointer", fontSize:".8rem", color:"#6ee7b7", fontWeight:600,
                    }}>
                      📸 Take Photo
                      <input type="file" accept="image/*" style={{ display:"none" }}
                        onChange={e => {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          const reader = new FileReader();
                          reader.onload = ev => setStudentAvatar(ev.target.result);
                          reader.readAsDataURL(file);
                        }} />
                    </label>
                  ) : (
                    <button type="button"
                      onClick={() => setShowWebcam(true)}
                      style={{
                        flex:1, display:"flex", alignItems:"center", justifyContent:"center", gap:6,
                        background:"rgba(16,185,129,.08)", border:"1px solid rgba(16,185,129,.2)",
                        borderRadius:8, padding:"8px 12px", cursor:"pointer", fontSize:".8rem", color:"#6ee7b7", fontWeight:600,
                      }}>
                      📸 Take Photo
                    </button>
                  )}
                </div>
              </div>

              {createStudentError && (
                <div style={{ background:"rgba(239,68,68,.1)", border:"1px solid rgba(239,68,68,.3)", borderRadius:10, padding:"12px 14px", marginBottom:14, fontSize:".85rem", color:"#fca5a5", whiteSpace:"pre-line" }}>
                  {createStudentError}
                  {(createStudentError.includes("log out") || createStudentError.includes("Session")) && (
                    <div style={{ marginTop:8 }}>
                      <button
                        type="button"
                        onClick={() => { window.location.href = "/"; localStorage.removeItem("tutor_user"); localStorage.removeItem("tutor_active_page"); window.location.reload(); }}
                        style={{ background:"rgba(239,68,68,.2)", border:"1px solid rgba(239,68,68,.4)", borderRadius:7, padding:"6px 14px", color:"#fca5a5", cursor:"pointer", fontFamily:"inherit", fontSize:".8rem", fontWeight:700 }}>
                        🔒 Log out now
                      </button>
                    </div>
                  )}
                </div>
              )}
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
                autoComplete="off"
              />
              <small style={{ color: "#888", fontSize: "0.78rem", marginTop: -6 }}>
                Leave blank if the student does not have an email — they can log in with their username and password.
              </small>

              <label style={{ display:"block", marginBottom:4, fontSize:".85rem", fontWeight:600 }}>
                Child's Class *
              </label>
              <select
                value={studentGrade}
                onChange={(e) => { setStudentGrade(e.target.value); setStudentStream(""); }}
                required
                style={{ marginBottom:12 }}
              >
                <option value="">— Select class —</option>
                {["Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"].map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
              {isStreamGrade(studentGrade) && (
                <>
                  <label style={{ display:"block", marginBottom:4, fontSize:".85rem", fontWeight:600 }}>
                    Stream *
                  </label>
                  <select
                    value={studentStream}
                    onChange={(e) => setStudentStream(e.target.value)}
                    required
                    style={{ marginBottom:6 }}
                  >
                    <option value="">— Select stream —</option>
                    {GRADE_11_12_STREAMS.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                  <small style={{ color: "#888", fontSize: "0.75rem", marginBottom:10, display:"block" }}>
                    Stream determines which subjects appear in your child's lessons.
                  </small>
                </>
              )}

              <input
                type="text"
                placeholder="Set a password for your child"
                value={studentPassword}
                onChange={(e) => setStudentPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
              <small style={{ color: "#888", fontSize: "0.78rem", marginTop: -6 }}>
                👁️ Visible so you can confirm it — you will share this with your child
              </small>

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

      {/* ── Child credentials card shown after successful creation ── */}
      {createdChildInfo && (
        <div className="modal-backdrop">
          <div className="premium-modal" style={{ maxWidth: 480 }}>
            <button className="modal-close" onClick={() => setCreatedChildInfo(null)}>×</button>
            <h3 style={{ color: "#16a34a", marginBottom: 8 }}>✅ Child account created!</h3>
            <p style={{ fontSize: ".9rem", marginBottom: 16 }}>
              Share these details with your child so they can log in.
            </p>

            {/* Credentials */}
            <div style={{ background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 10, padding: "12px 14px", marginBottom: 14, fontFamily: "monospace", fontSize: ".85rem" }}>
              <div style={{ marginBottom: 6 }}>
                <span style={{ fontWeight: 600 }}>Name (username): </span>
                <strong style={{ color: "#4f46e5" }}>{createdChildInfo.username}</strong>
                <button onClick={() => navigator.clipboard.writeText(createdChildInfo.username)}
                  style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#6366f1", fontSize: ".7rem", fontWeight: 700 }}>📋</button>
              </div>
              {createdChildInfo.email && (
                <div style={{ marginBottom: 6 }}>
                  <span style={{ fontWeight: 600 }}>Email: </span>
                  <strong style={{ color: "#4f46e5" }}>{createdChildInfo.email}</strong>
                  <button onClick={() => navigator.clipboard.writeText(createdChildInfo.email)}
                    style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#6366f1", fontSize: ".7rem", fontWeight: 700 }}>📋</button>
                </div>
              )}
              <div>
                <span style={{ fontWeight: 600 }}>Password: </span>
                <strong style={{ color: "#d97706" }}>{createdChildInfo.password}</strong>
                <button onClick={() => navigator.clipboard.writeText(createdChildInfo.password)}
                  style={{ marginLeft: 8, background: "none", border: "none", cursor: "pointer", color: "#6366f1", fontSize: ".7rem", fontWeight: 700 }}>📋</button>
              </div>
            </div>

            {/* One-click auto-login link (includes encoded password) */}
            {(() => {
              const loginId = createdChildInfo.email || createdChildInfo.username;
              const encodedPass = btoa(createdChildInfo.password);
              const autoLoginLink = `https://likhapoha.in/?u=${encodeURIComponent(loginId)}&p=${encodedPass}`;
              return (
                <div style={{ marginBottom: 14 }}>
                  <p style={{ fontSize: ".78rem", color: "#4f46e5", margin: "0 0 6px", fontWeight: 700 }}>
                    🔗 One-click login link (logs in directly to child's dashboard)
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.2)", borderRadius: 8, padding: "6px 10px", flexWrap: "wrap" }}>
                    <a href={autoLoginLink} target="_blank" rel="noreferrer"
                      style={{ fontSize: ".7rem", color: "#4f46e5", fontFamily: "monospace", flex: 1, wordBreak: "break-all", textDecoration: "underline", cursor: "pointer" }}>
                      {autoLoginLink.substring(0, 60)}…
                    </a>
                    <button onClick={() => navigator.clipboard.writeText(autoLoginLink)}
                      style={{ background: "#6366f1", border: "none", borderRadius: 6, padding: "3px 10px", color: "#fff", cursor: "pointer", fontSize: ".72rem", fontWeight: 700, fontFamily: "inherit", whiteSpace: "nowrap" }}>
                      📋 Copy
                    </button>
                  </div>
                  <p style={{ fontSize: ".72rem", color: "#64748b", margin: "4px 0 0" }}>
                    Click this link to sign in directly to your child's account — no username or password needed.
                  </p>
                </div>
              );
            })()}

            {/* Next steps */}
            <div style={{ fontSize: ".83rem", lineHeight: 1.7, marginBottom: 16 }}>
              <strong style={{ display: "block", marginBottom: 6 }}>📋 What to do next:</strong>
              <ol style={{ paddingLeft: 18, margin: 0 }}>
                <li>Share the <strong>username or email + password</strong> with your child</li>
                <li>Child can log in at <strong>likhapoha.in</strong> using username OR email</li>
                <li>Child can <strong>change their password</strong> from their profile anytime</li>
                <li style={{ color: "#4f46e5", fontWeight: 600 }}>💡 Sit with your child for their first login and give a quick walkthrough</li>
              </ol>
            </div>

            {/* Video walkthrough — now live */}
            <div style={{ background: "rgba(99,102,241,.08)", border: "1px solid rgba(99,102,241,.25)", borderRadius: 8, padding: "10px 14px", textAlign: "center", marginBottom: 16 }}>
              <div style={{ fontSize: "1.4rem", marginBottom: 3 }}>▶️</div>
              <p style={{ fontSize: ".78rem", color: "#4f46e5", margin: 0, fontWeight: 700 }}>Watch the Platform Walkthrough Video</p>
              <p style={{ fontSize: ".7rem", color: "#475569", margin: "3px 0 0 0" }}>Available in English and Hindi — helps your child get started on Likha Poha AI</p>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 8 }}>
                <a href="https://youtu.be/N82gfHBJm00" target="_blank" rel="noreferrer"
                  style={{ background: "#6366f1", border: "none", borderRadius: 6, padding: "5px 14px", color: "#fff", fontSize: ".75rem", fontWeight: 700, textDecoration: "none" }}>
                  🇬🇧 English
                </a>
                <a href="https://youtu.be/y0YHnMrmR3k" target="_blank" rel="noreferrer"
                  style={{ background: "#6366f1", border: "none", borderRadius: 6, padding: "5px 14px", color: "#fff", fontSize: ".75rem", fontWeight: 700, textDecoration: "none" }}>
                  🇮🇳 Hindi
                </a>
              </div>
            </div>

            <button className="primary-btn" style={{ width: "100%" }} onClick={() => setCreatedChildInfo(null)}>
              Done ✓
            </button>
          </div>
        </div>
      )}

      {/* ── Desktop webcam capture modal ── */}
      {showWebcam && (
        <WebcamCaptureModal
          onCapture={(dataUrl) => { setStudentAvatar(dataUrl); setShowWebcam(false); }}
          onClose={() => setShowWebcam(false)}
        />
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

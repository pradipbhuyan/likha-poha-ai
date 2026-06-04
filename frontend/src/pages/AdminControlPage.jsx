import { useEffect, useState } from "react";
import {
  getAdminFamilies,
  createAdminParent,
  createAdminChild,
  createAdminTeacher,
  assignTeacherStudent,
  deleteTeacherAssignment,
  updateChildAccess,
  updateChildLimits,
  deleteUser,
} from "../api/adminControl";
import {
  SUBSCRIPTION_PLAN_ORDER,
  SUBSCRIPTION_PLANS,
} from "../config/subscriptionPlans";

const STUDENT_GRADE_OPTIONS = Array.from(
  { length: 10 },
  (_, index) => `Grade ${index + 1}`
);

const AI_MODEL_OPTIONS = [
  {
    value: "default",
    label: "Default (GPT-4.1 mini; Family Premium auto GPT-5)",
  },
  {
    value: "gpt-5",
    label: "GPT-5",
  },
  {
    value: "gpt-5-mini",
    label: "GPT-5 mini",
  },
];

function AdminControlPage({ user }) {
  /** Admin operations page for managing families, access flags, subscriptions, and AI limits. */
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [parentForm, setParentForm] = useState({
    email: "",
    password: "",
    username: "",
  });

  const [teacherForm, setTeacherForm] = useState({
    email: "",
    password: "",
    username: "",
    teacher_type: "independent",
    school_name: "",
    subjectsCsv: "Science, Maths, English",
    gradesCsv: "Grade 9",
    status: "active",
  });

  const [childForms, setChildForms] = useState({});
  const [assignmentForms, setAssignmentForms] = useState({});

  async function loadFamilies() {
    /** Fetch all families with their parents and children for admin editing. */
    try {
      const data = await getAdminFamilies(user.accessToken);
      setFamilies(data.families || []);
    } catch (err) {
      console.error(err);
      setError("Unable to load admin control data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user?.accessToken) {
      loadFamilies();
    }
  }, [user?.accessToken]);

  async function handleCreateParent(e) {
    /** Create a parent account and refresh the family list. */
    e.preventDefault();
    setMessage("");
    setError("");

    try {
      await createAdminParent(parentForm, user.accessToken);

      setParentForm({
        email: "",
        password: "",
        username: "",
      });

      await loadFamilies();
      setMessage("Parent created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create parent.");
    }
  }

  async function handleCreateChild(e, familyId, parentId) {
    /** Create a child account under an existing family and parent. */
    e.preventDefault();
    setMessage("");
    setError("");

    const form = childForms[parentId] || {
      email: "",
      password: "",
      username: "",
      grade: "Grade 9",
    };

    try {
      await createAdminChild(
        {
          ...form,
          parent_id: parentId,
          family_id: familyId,
        },
        user.accessToken
      );

      setChildForms((prev) => ({
        ...prev,
        [parentId]: {
          email: "",
          password: "",
          username: "",
          grade: "Grade 9",
        },
      }));

      await loadFamilies();
      setMessage("Child created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create child.");
    }
  }

  function parseCsvList(value) {
    /** Convert admin comma-separated inputs into clean API arrays. */
    return String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function handleCreateTeacher(e) {
    /** Create a teacher account that can later be assigned students. */
    e.preventDefault();
    setMessage("");
    setError("");

    try {
      await createAdminTeacher(
        {
          email: teacherForm.email,
          password: teacherForm.password,
          username: teacherForm.username,
          teacher_type: teacherForm.teacher_type,
          school_name: teacherForm.school_name,
          subjects: parseCsvList(teacherForm.subjectsCsv),
          grades: parseCsvList(teacherForm.gradesCsv),
          status: teacherForm.status,
        },
        user.accessToken
      );

      setTeacherForm({
        email: "",
        password: "",
        username: "",
        teacher_type: "independent",
        school_name: "",
        subjectsCsv: "Science, Maths, English",
        gradesCsv: "Grade 9",
        status: "active",
      });

      await loadFamilies();
      setMessage("Teacher created successfully.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to create teacher.");
    }
  }

  async function handleAssignTeacherStudent(e, teacher, allStudents) {
    /** Link one existing student to a teacher with optional class context. */
    e.preventDefault();
    setMessage("");
    setError("");

    const form = assignmentForms[teacher.id] || {};
    const studentId = form.student_id || allStudents[0]?.id;
    const student = allStudents.find((item) => item.id === studentId);

    if (!studentId) {
      setError("Create a student before assigning them to a teacher.");
      return;
    }

    try {
      await assignTeacherStudent(
        {
          teacher_id: teacher.id,
          student_id: studentId,
          grade: form.grade || student?.grade || "Grade 9",
          subject: form.subject || "",
          section: form.section || "",
        },
        user.accessToken
      );

      setAssignmentForms((prev) => ({
        ...prev,
        [teacher.id]: {
          student_id: "",
          subject: "",
          section: "",
        },
      }));

      await loadFamilies();
      setMessage(`Student assigned to ${teacher.username}.`);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to assign student.");
    }
  }

  async function removeTeacherAssignment(assignmentId) {
    /** Remove one teacher-student link and refresh the admin page. */
    setMessage("");
    setError("");

    try {
      await deleteTeacherAssignment(assignmentId, user.accessToken);
      await loadFamilies();
      setMessage("Teacher assignment removed.");
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to remove teacher assignment.");
    }
  }

  async function saveAccess(child) {
    /** Persist the subject access flags and account status for one child. */
    setMessage("");
    setError("");

    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
          grade: child.grade || "Grade 9",
          ai_model_preference: child.ai_model_preference || "default",
        },
        user.accessToken
      );

      await loadFamilies();
      setMessage(`Access saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save access.");
    }
  }

  async function suspendChild(child) {
    /** Mark a child account as suspended using the same plan-saving path. */
    const updatedChild = {
      ...child,
      account_status: "suspended",
    };
  
    await savePlan(updatedChild);
  }
  
  async function reactivateChild(child) {
    /** Restore a suspended child account to active status. */
    const updatedChild = {
      ...child,
      account_status: "active",
    };
  
    await savePlan(updatedChild);
  }

  async function savePlan(child) {
    /** Save both subscription access and token limits so plan changes stay consistent. */
    setMessage("");
    setError("");
  
    try {
      await updateChildAccess(
        child.id,
        {
          access_cbse: !!child.access_cbse,
          access_sof_science: !!child.access_sof_science,
          access_sof_maths: !!child.access_sof_maths,
          access_sof_english: !!child.access_sof_english,
          subscription_plan: child.subscription_plan || "free",
          account_status: child.account_status || "active",
          grade: child.grade || "Grade 9",
          ai_model_preference: child.ai_model_preference || "default",
        },
        user.accessToken
      );
  
      await updateChildLimits(
        child.id,
        {
          daily_token_limit: Number(child.daily_token_limit || 0),
          monthly_token_limit: Number(child.monthly_token_limit || 0),
        },
        user.accessToken
      );
  
      await loadFamilies();
      setMessage(`Plan saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save plan.");
    }
  }

  async function saveLimits(child) {
    /** Save only token limits when the admin edits usage caps directly. */
    setMessage("");
    setError("");

    try {
      await updateChildLimits(
        child.id,
        {
          daily_token_limit: Number(child.daily_token_limit || 0),
          monthly_token_limit: Number(child.monthly_token_limit || 0),
        },
        user.accessToken
      );

      await loadFamilies();
      setMessage(`Limits saved for ${child.username}.`);
    } catch (err) {
      console.error(err);
      setError("Unable to save limits.");
    }
  }

  async function removeUser(userId) {
    /** Delete a user after confirmation and reload the admin roster. */
    setMessage("");
    setError("");

    if (!window.confirm("Delete this user? This cannot be undone.")) return;

    try {
      await deleteUser(userId, user.accessToken);
      await loadFamilies();
      setMessage("User deleted successfully.");
    } catch (err) {
      console.error(err);
      setError("Unable to delete user.");
    }
  }

  function applyPlanPreset(familyId, childId, planName) {
    /** Apply a configured subscription preset to local child state before saving it. */
    const preset = SUBSCRIPTION_PLANS[planName];
  
    if (!preset) return;
  
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;
  
        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId
              ? {
                  ...child,
                  subscription_plan: planName,
                  access_cbse: preset.access_cbse,
                  access_sof_science: preset.access_sof_science,
                  access_sof_maths: preset.access_sof_maths,
                  access_sof_english: preset.access_sof_english,
                  daily_token_limit: preset.daily_token_limit,
                  monthly_token_limit: preset.monthly_token_limit,
                }
              : child
          ),
        };
      })
    );
  }


  function updateLocalChild(familyId, childId, field, value) {
    /** Update a child field locally inside the nested family list. */
    setFamilies((prev) =>
      prev.map((family) => {
        if (family.family_id !== familyId) return family;

        return {
          ...family,
          children: family.children.map((child) =>
            child.id === childId ? { ...child, [field]: value } : child
          ),
        };
      })
    );
  }

  function updateChildForm(parentId, field, value) {
    /** Track per-parent child creation forms without mixing family rows. */
    setChildForms((prev) => ({
      ...prev,
      [parentId]: {
        email: "",
        password: "",
        username: "",
        ...(prev[parentId] || {}),
        [field]: value,
      },
    }));
  }

  function updateAssignmentForm(teacherId, field, value) {
    /** Track per-teacher student assignment forms independently. */
    setAssignmentForms((prev) => ({
      ...prev,
      [teacherId]: {
        ...(prev[teacherId] || {}),
        [field]: value,
      },
    }));
  }

  if (loading) return <p>Loading admin control...</p>;

  const allTeachers = families.flatMap((family) => family.teachers || []);
  const allStudents = families.flatMap((family) => family.children || []);
  const studentById = Object.fromEntries(
    allStudents.map((student) => [student.id, student])
  );

  return (
    <div className="premium-page">
      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <h2>🛠️ Admin Control Center</h2>
          <p>Manage families, children, learning access, and AI limits.</p>
        </div>
      </section>

      {message && <div className="info-box">{message}</div>}
      {error && <div className="error-box">{error}</div>}

      <section className="premium-section">
        <div className="premium-header">
          <h3>➕ Create New Parent</h3>
          <p>Create a new family with one parent account.</p>
        </div>

        <form
          onSubmit={handleCreateParent}
          className="form-grid premium-rag-form-grid"
        >
          <label>
            Parent Name
            <input
              type="text"
              value={parentForm.username}
              onChange={(e) =>
                setParentForm((prev) => ({
                  ...prev,
                  username: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Parent Email
            <input
              type="email"
              value={parentForm.email}
              onChange={(e) =>
                setParentForm((prev) => ({
                  ...prev,
                  email: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Temporary Password
            <input
              type="password"
              value={parentForm.password}
              onChange={(e) =>
                setParentForm((prev) => ({
                  ...prev,
                  password: e.target.value,
                }))
              }
              required
            />
          </label>

          <button className="primary-btn" type="submit">
            Create Parent
          </button>
        </form>
      </section>

      <section className="premium-section">
        <div className="premium-header">
          <p className="eyebrow">Teacher Access</p>
          <h3>Teacher Accounts</h3>
          <p>
            Create teacher logins for schools or independent teachers. Public
            signup remains parent-only.
          </p>
        </div>

        <form
          onSubmit={handleCreateTeacher}
          className="form-grid premium-rag-form-grid"
        >
          <label>
            Teacher Name
            <input
              type="text"
              value={teacherForm.username}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  username: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Teacher Email
            <input
              type="email"
              value={teacherForm.email}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  email: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Temporary Password
            <input
              type="password"
              value={teacherForm.password}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  password: e.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Teacher Type
            <select
              value={teacherForm.teacher_type}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  teacher_type: e.target.value,
                }))
              }
            >
              <option value="independent">Independent Teacher</option>
              <option value="school">School Teacher</option>
            </select>
          </label>

          <label>
            School / Organization
            <input
              type="text"
              value={teacherForm.school_name}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  school_name: e.target.value,
                }))
              }
              placeholder="Optional for independent teachers"
            />
          </label>

          <label>
            Status
            <select
              value={teacherForm.status}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  status: e.target.value,
                }))
              }
            >
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>

          <label>
            Subjects
            <input
              type="text"
              value={teacherForm.subjectsCsv}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  subjectsCsv: e.target.value,
                }))
              }
              placeholder="Science, Maths, English"
            />
          </label>

          <label>
            Grades
            <input
              type="text"
              value={teacherForm.gradesCsv}
              onChange={(e) =>
                setTeacherForm((prev) => ({
                  ...prev,
                  gradesCsv: e.target.value,
                }))
              }
              placeholder="Grade 6, Grade 7, Grade 9"
            />
          </label>

          <button className="primary-btn" type="submit">
            Create Teacher
          </button>
        </form>

        <div style={{ marginTop: 24 }}>
          <h4>Current Teachers</h4>

          {allTeachers.length === 0 ? (
            <div className="info-box">
              No teacher accounts yet. Create one above, then assign students.
            </div>
          ) : (
            allTeachers.map((teacher) => {
              const metadata = teacher.teacher_profile || {};
              const form = assignmentForms[teacher.id] || {};

              return (
                <div
                  key={teacher.id}
                  className="premium-card"
                  style={{ marginBottom: 18 }}
                >
                  <div className="premium-rag-result-row success">
                    <div>
                      <strong>{teacher.username}</strong>
                      <p>{teacher.email}</p>
                      <small>
                        {metadata.teacher_type || "independent"}
                        {metadata.school_name ? ` • ${metadata.school_name}` : ""}
                      </small>
                    </div>

                    <button
                      className="danger-btn"
                      onClick={() => removeUser(teacher.id)}
                    >
                      Delete Teacher
                    </button>
                  </div>

                  <div className="family-summary-row" style={{ marginTop: 14 }}>
                    <span>
                      Subjects: {(metadata.subjects || []).join(", ") || "Any"}
                    </span>
                    <span>
                      Grades: {(metadata.grades || []).join(", ") || "Any"}
                    </span>
                  </div>

                  <form
                    onSubmit={(e) =>
                      handleAssignTeacherStudent(e, teacher, allStudents)
                    }
                    className="form-grid premium-rag-form-grid"
                    style={{ marginTop: 18 }}
                  >
                    <label>
                      Assign Student
                      <select
                        value={form.student_id || ""}
                        onChange={(e) => {
                          const selected = studentById[e.target.value];
                          updateAssignmentForm(
                            teacher.id,
                            "student_id",
                            e.target.value
                          );
                          updateAssignmentForm(
                            teacher.id,
                            "grade",
                            selected?.grade || "Grade 9"
                          );
                        }}
                      >
                        <option value="">Select student</option>
                        {allStudents.map((student) => (
                          <option key={student.id} value={student.id}>
                            {student.username} ({student.grade || "Grade 9"})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Subject
                      <input
                        value={form.subject || ""}
                        onChange={(e) =>
                          updateAssignmentForm(
                            teacher.id,
                            "subject",
                            e.target.value
                          )
                        }
                        placeholder="Science"
                      />
                    </label>

                    <label>
                      Section / Group
                      <input
                        value={form.section || ""}
                        onChange={(e) =>
                          updateAssignmentForm(
                            teacher.id,
                            "section",
                            e.target.value
                          )
                        }
                        placeholder="9A or Pradip batch"
                      />
                    </label>

                    <button className="secondary-btn" type="submit">
                      Assign Student
                    </button>
                  </form>

                  {(teacher.assignments || []).length > 0 && (
                    <div style={{ marginTop: 18 }}>
                      <h4>Assigned Students</h4>
                      {(teacher.assignments || []).map((assignment) => {
                        const assignedStudent =
                          studentById[assignment.student_id] || {};

                        return (
                          <div
                            key={
                              assignment.id ||
                              `${assignment.student_id}-${assignment.subject}`
                            }
                            className="premium-rag-result-row success"
                            style={{ marginBottom: 10 }}
                          >
                            <div>
                              <strong>
                                {assignedStudent.username ||
                                  assignment.student_id}
                              </strong>
                              <p>
                                {assignment.grade || "Grade 9"} •{" "}
                                {assignment.subject || "General"}
                                {assignment.section
                                  ? ` • ${assignment.section}`
                                  : ""}
                              </p>
                            </div>

                            {assignment.id && (
                              <button
                                className="secondary-btn"
                                onClick={() =>
                                  removeTeacherAssignment(assignment.id)
                                }
                              >
                                Remove
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </section>

      {families.map((family) => (
        <section key={family.family_id} className="premium-section">
          <div className="premium-header">
            <h3>Family: {family.family_id}</h3>
          </div>

          <h4>Parents</h4>

          {(family.parents || []).map((parent) => {
            const childForm = childForms[parent.id] || {
              email: "",
              password: "",
              username: "",
            };

            return (
              <div
                key={parent.id}
                className="premium-card"
                style={{ marginBottom: 18 }}
              >
                <div className="premium-rag-result-row success">
                  <div>
                    <strong>{parent.username}</strong>
                    <p>{parent.email}</p>
                    <small>{parent.role}</small>
                  </div>

                  <button
                    className="danger-btn"
                    onClick={() => removeUser(parent.id)}
                  >
                    Delete Parent
                  </button>
                </div>

                <div style={{ marginTop: 18 }}>
                  <h4>Create Child Under {parent.username}</h4>

                  <form
                    onSubmit={(e) =>
                      handleCreateChild(e, family.family_id, parent.id)
                    }
                    className="form-grid premium-rag-form-grid"
                  >
                    <label>
                      Child Name
                      <input
                        type="text"
                        value={childForm.username}
                        onChange={(e) =>
                          updateChildForm(parent.id, "username", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Child Email
                      <input
                        type="email"
                        value={childForm.email}
                        onChange={(e) =>
                          updateChildForm(parent.id, "email", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Temporary Password
                      <input
                        type="password"
                        value={childForm.password}
                        onChange={(e) =>
                          updateChildForm(parent.id, "password", e.target.value)
                        }
                        required
                      />
                    </label>

                    <label>
                      Class
                      <select
                        value={childForm.grade || "Grade 9"}
                        onChange={(e) =>
                          updateChildForm(parent.id, "grade", e.target.value)
                        }
                      >
                        {STUDENT_GRADE_OPTIONS.map((gradeOption) => (
                          <option key={gradeOption} value={gradeOption}>
                            {gradeOption}
                          </option>
                        ))}
                      </select>
                    </label>

                    <button className="secondary-btn" type="submit">
                      Create Child
                    </button>
                  </form>
                </div>
              </div>
            );
          })}

          <h4 style={{ marginTop: 24 }}>Children</h4>

          {(family.children || []).map((child) => (
            <div
              key={child.id}
              className="premium-card"
              style={{ marginBottom: 18 }}
            >
              <h3>{child.username}</h3>
              <p>
                {child.email} • {child.grade || "Grade 9"}
              </p>

              {child.activity && (
                <div
                  className="premium-card"
                  style={{
                    marginTop: 14,
                    marginBottom: 18,
                    padding: 16,
                  }}
                >
                  <h4>📊 Student Activity</h4>

                  <div className="form-grid premium-rag-form-grid">
                    <div>
                      <strong>{child.activity.lessons_generated || 0}</strong>
                      <p>Lessons</p>
                    </div>

                    <div>
                      <strong>{child.activity.doubts_asked || 0}</strong>
                      <p>Doubts</p>
                    </div>

                    <div>
                      <strong>
                        {child.activity.mock_tests_generated || 0}
                      </strong>
                      <p>Mock Tests</p>
                    </div>

                    <div>
                      <strong>{child.activity.requests_total || 0}</strong>
                      <p>Total AI Requests</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_today || 0}</strong>
                      <p>Tokens Today</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_this_month || 0}</strong>
                      <p>Tokens This Month</p>
                    </div>

                    <div>
                      <strong>{child.activity.tokens_total || 0}</strong>
                      <p>Total Tokens</p>
                    </div>

                    <div>
                      <strong>
                        ${Number(child.activity.cost_total || 0).toFixed(6)}
                      </strong>
                      <p>Total Cost</p>
                    </div>
                  </div>

                  <small>
                    Last Activity:{" "}
                    {child.activity.last_activity
                      ? child.activity.last_activity.slice(0, 19)
                      : "No activity yet"}
                  </small>
                </div>
              )}

              <div className="form-grid premium-rag-form-grid">
                <label>
                  Class
                  <select
                    value={child.grade || "Grade 9"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "grade",
                        e.target.value
                      )
                    }
                  >
                    {STUDENT_GRADE_OPTIONS.map((gradeOption) => (
                      <option key={gradeOption} value={gradeOption}>
                        {gradeOption}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Plan
                  <select
                    value={child.subscription_plan || "free"}
                    onChange={(e) =>
                      applyPlanPreset(
                        family.family_id,
                        child.id,
                        e.target.value
                      )
                    }
                  >
                    {SUBSCRIPTION_PLAN_ORDER.map((planKey) => (
                      <option key={planKey} value={planKey}>
                        {SUBSCRIPTION_PLANS[planKey].label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Status
                  <select
                    value={child.account_status || "active"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "account_status",
                        e.target.value
                      )
                    }
                  >
                    <option value="active">Active</option>
                    <option value="trial">Trial</option>
                    <option value="suspended">Suspended</option>
                    <option value="expired">Expired</option>
                  </select>
                </label>

                <label>
                  Daily Tokens
                  <input
                    type="number"
                    value={child.daily_token_limit || 0}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "daily_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  Monthly Tokens
                  <input
                    type="number"
                    value={child.monthly_token_limit || 0}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "monthly_token_limit",
                        e.target.value
                      )
                    }
                  />
                </label>

                <label>
                  AI Model for SOF Mock & Doubts
                  <select
                    value={child.ai_model_preference || "default"}
                    onChange={(e) =>
                      updateLocalChild(
                        family.family_id,
                        child.id,
                        "ai_model_preference",
                        e.target.value
                      )
                    }
                  >
                    {AI_MODEL_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div style={{ marginTop: 16 }}>
                {[
                  ["access_cbse", "CBSE"],
                  ["access_sof_science", "SOF Science"],
                  ["access_sof_maths", "SOF Maths"],
                  ["access_sof_english", "SOF English"],
                ].map(([field, label]) => (
                  <label
                    key={field}
                    style={{ display: "block", marginBottom: 8 }}
                  >
                    <input
                      type="checkbox"
                      checked={!!child[field]}
                      onChange={(e) =>
                        updateLocalChild(
                          family.family_id,
                          child.id,
                          field,
                          e.target.checked
                        )
                      }
                    />{" "}
                    {label}
                  </label>
                ))}
              </div>

              <div style={{ display: "flex", gap: 12, marginTop: 18 }}>
                <button className="primary-btn" onClick={() => savePlan(child)}>
                  💾 Save Plan
                </button>

                <button
                  className="primary-btn"
                  onClick={() => saveAccess(child)}
                >
                  Save Access
                </button>

                <button
                  className="secondary-btn"
                  onClick={() => saveLimits(child)}
                >
                  Save Limits
                </button>
                {child.account_status === "suspended" ? (
                  <button
                    className="primary-btn"
                    onClick={() => reactivateChild(child)}
                  >
                    🔓 Reactivate
                  </button>
                ) : (
                  <button
                    className="secondary-btn"
                    onClick={() => suspendChild(child)}
                  >
                    🔒 Suspend
                  </button>
                )}

                <button
                  className="danger-btn"
                  onClick={() => removeUser(child.id)}
                >
                  Delete Child
                </button>
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

export default AdminControlPage;

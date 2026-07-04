import { useState, useEffect } from "react";
import logo from "../assets/AITutorLogo1.png";

import { BookOpen, Brain, ClipboardList, BarChart3 } from "lucide-react";

import { supabase } from "../api/supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/** Initiates Google OAuth redirect via Supabase. */
async function signInWithGoogle() {
  await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
      queryParams: { access_type: "offline", prompt: "select_account" },
    },
  });
}

const PASSWORD_RESET_REDIRECT_URL =
  import.meta.env.VITE_PASSWORD_RESET_REDIRECT_URL ||
  `${window.location.origin}/reset-password`;

function LoginPage({ onLogin, onShowSignup }) {
  /** Handles Supabase authentication and parent signup for the app entry point. */
  const [isSignupMode, setIsSignupMode] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [loading, setLoading] = useState(false);

// Pre-fill username AND auto-login from URL params
// ?u= pre-fills the username field
// ?p= (base64-encoded password) + ?u= triggers auto-login → lands on child dashboard
useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const prefilledUser = params.get("u");
    const encodedPass = params.get("p");
    if (prefilledUser) {
      const decoded = decodeURIComponent(prefilledUser);
      setUsername(decoded);
      // Auto-login if password is also provided (parent launching child's account)
      if (encodedPass) {
        try {
          const decodedPass = atob(encodedPass);
          setPassword(decodedPass);
          // Trigger login automatically after a brief render tick
          setTimeout(async () => {
            try {
              setLoading(true);
              setError("");
              let loginEmail = decoded;
              if (!loginEmail.includes("@")) {
                const resp = await fetch(
                  `${API_BASE_URL}/api/auth/lookup-email/${encodeURIComponent(loginEmail)}`
                );
                if (resp.ok) {
                  const r = await resp.json();
                  loginEmail = r.email || loginEmail;
                }
              }
              await supabase.auth.signOut().catch(() => {});
              const { data, error: signInErr } = await supabase.auth.signInWithPassword({
                email: loginEmail,
                password: decodedPass,
              });
              if (!signInErr && data?.session) {
                const { data: profile } = await supabase
                  .from("profiles").select("*").eq("id", data.user.id).single();
                if (profile) {
                  onLogin(await buildLoginUser({
                    authUser: data.user,
                    profile,
                    accessToken: data.session.access_token,
                  }));
                }
              } else {
                setError("Auto-login failed. Please sign in manually.");
                setLoading(false);
              }
            } catch {
              setError("Auto-login failed. Please sign in manually.");
              setLoading(false);
            }
          }, 200);
        } catch {
          // Invalid base64 — just pre-fill username
        }
      }
    }
  }, []);

  async function buildLoginUser({ authUser, profile, accessToken }) {
    /** Convert Supabase auth/profile rows into the app's normalized user object. */
    return {
      id: authUser.id,
      email: authUser.email,
      username: profile.username || authUser.email,
	      role: profile.role,
	      grade: profile.grade || "Grade 9",
      board: profile.board || "CBSE",
	      parentId: profile.parent_id,
      familyId: profile.family_id,

      accessToken,

      accessCbse: !!profile.access_cbse,
      accessSofScience: !!profile.access_sof_science,
      accessSofMaths: !!profile.access_sof_maths,
      accessSofEnglish: !!profile.access_sof_english,
      cbseSubjects: Array.isArray(profile.cbse_subjects)
        ? profile.cbse_subjects
        : [],
      avatar: profile.avatar || "",

      dailyTokenLimit: profile.daily_token_limit,
      monthlyTokenLimit: profile.monthly_token_limit,
      subscriptionPlan: profile.subscription_plan || "free",
      accountStatus: profile.account_status || "active",
      // Always fetch offer validity for all users — offer code users can have
      // access_cbse = true AND a valid offer redemption. We need the expiry date
      // to show in SubscriptionPlansPage and to know when to revoke access.
      ...(await (async () => {
        try {
          const r = await fetch(`${API_BASE_URL}/api/offer/my-access`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          });
          if (!r.ok) return { offerAccess: false };
          const d = await r.json();
          return {
            offerAccess: !!d.has_offer_access,
            offerValidUntil: d.valid_until || null,
            offerDaysRemaining: d.days_remaining ?? null,
            offerExpiringSoon: !!d.expiring_soon,
            offerExpiredOn: d.expired_on || null,
          };
        } catch { return { offerAccess: false }; }
      })()),
    };
  }

  async function handleLogin(e) {
    /** Resolve username or email, authenticate with Supabase, then load profile access flags. */
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      let loginEmail = username.trim();

      if (!loginEmail.includes("@")) {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/lookup-email/${encodeURIComponent(loginEmail)}`
        );

        if (!response.ok) {
          let detail = "Username not found.";

          try {
            const result = await response.json();
            detail = result.detail || detail;
          } catch {
            // Keep the friendly default when the API returns no JSON body.
          }

          setError(detail);
          return;
        }

        const result = await response.json();
        loginEmail = result.email;
      }

      // Ensure any stale recovery/invite session is cleared before fresh login.
      // signOut() is a no-op when there is no active session.
      await supabase.auth.signOut().catch(() => {});

      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginEmail,
        password,
      });

      if (error) {
        const msg = error.message || "";

        if (
          msg.toLowerCase().includes("email not confirmed") ||
          msg.toLowerCase().includes("email_not_confirmed")
        ) {
          setError(
            "📧 Your email address has not been verified yet. Please check your inbox for a confirmation email and click the link to activate your account. Check your spam folder if you don't see it."
          );
        } else if (msg.toLowerCase().includes("invalid login credentials")) {
          setError("Incorrect username or password. Please try again.");
        } else {
          setError(msg || "Login failed. Please try again.");
        }

        return;
      }

      const { data: profile, error: profileError } = await supabase
        .from("profiles")
	        .select("*")
        .eq("id", data.user.id)
        .single();

      if (profileError) {
        setError("Login successful, but profile role was not found.");
        return;
      }

      if (!data.session) {
        // This can happen if Supabase requires an additional verification step.
        setError(
          "Sign-in could not be completed. Please request a new password reset link from the Forgot Password page."
        );
        return;
      }

      onLogin(
        await buildLoginUser({
          authUser: data.user,
          profile,
          accessToken: data.session.access_token,
        })
      );
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function resolveLoginEmail(value) {
    /** Resolve an email or username into the email Supabase needs for auth actions. */
    const loginValue = value.trim();

    if (loginValue.includes("@")) {
      return loginValue;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/auth/lookup-email/${encodeURIComponent(loginValue)}`
    );

    if (!response.ok) {
      return "";
    }

    const result = await response.json();
    return result.email || "";
  }

  async function handleForgotPassword() {
    /**
     * Send a password reset email.
     * For students: also sends to the parent's email so parents can help their
     * child reset without the child needing access to their own inbox.
     */
    setError("");
    setInfoMessage("");

    if (!username.trim()) {
      setError("Enter your username or email first, then request a reset link.");
      return;
    }

    setLoading(true);

    try {
      // Use the backend endpoint which handles parent-email forwarding for children
      await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim() }),
      });
      setInfoMessage(
        "If this account exists, a reset link has been sent. For student accounts, the link is also sent to the parent's email."
      );
    } catch {
      setInfoMessage(
        "If this account exists, a password reset link has been sent."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSignup(e) {
    /** Create a parent family, profile, and authenticated session for new signup users. */
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signUp({
        email: username,
        password,
      });

      if (error) {
        const msg = error.message || "";

        if (msg.toLowerCase().includes("rate limit") || msg.toLowerCase().includes("over_email")) {
          setError(
            "⏳ Too many signup attempts. Supabase has temporarily limited email sending. Please wait a few minutes and try again."
          );
        } else {
          setError(msg || "Unable to create account.");
        }

        return;
      }

      if (!data.user) {
        setError("Unable to create account.");
        return;
      }

      // Check if a profile already exists for this user (re-submission after
      // a previous signup attempt with the same email).
      const { data: existingProfile } = await supabase
        .from("profiles")
        .select("id, family_id")
        .eq("id", data.user.id)
        .maybeSingle();

      let familyId = existingProfile?.family_id;

      if (!existingProfile) {
        // First signup attempt — create a new family and profile.
        familyId = crypto.randomUUID();

        const { error: familyError } = await supabase
          .from("families")
          .insert({
            id: familyId,
            family_name: `${fullName}'s Family`,
          });

        if (familyError) {
          setError(familyError.message);
          return;
        }

        const profilePayload = {
          id: data.user.id,
          email: username,
          username: fullName,
          role: "parent",
          parent_id: null,
          family_id: familyId,
          access_cbse: true,
          access_sof_science: false,
          access_sof_maths: false,
          access_sof_english: false,
          cbse_subjects: [],
          daily_token_limit: 50000,
          monthly_token_limit: 1000000,
          subscription_plan: "free",
          account_status: "active",
        };

        const { error: profileError } = await supabase
          .from("profiles")
          .insert(profilePayload);

        if (profileError) {
          setError(profileError.message);
          return;
        }
      }

      // When email confirmation is enabled in Supabase, signUp does not
      // return a session. Show a friendly message and stop here — the parent
      // must click the confirmation link before they can log in.
      if (!data.session) {
        setError("");
        setInfoMessage(
          "📧 Account created! A confirmation email has been sent to your inbox. Please click the link in that email to activate your account before signing in. Check your spam folder if you don't see it within a few minutes."
        );
        setIsSignupMode(false);
        return;
      }

      const profilePayload = existingProfile || {
        id: data.user.id,
        email: username,
        username: fullName,
        role: "parent",
        family_id: familyId,
      };

      const { data: loginData, error: loginError } =
        await supabase.auth.signInWithPassword({
          email: username,
          password,
        });

      if (loginError) {
        const msg = loginError.message || "";

        if (
          msg.toLowerCase().includes("email not confirmed") ||
          msg.toLowerCase().includes("email_not_confirmed")
        ) {
          setError("");
          setInfoMessage(
            "📧 Please confirm your email address first. Check your inbox for a confirmation link from Likha Poha AI. Check your spam folder if you don't see it."
          );
        } else {
          setError(msg || "Unable to sign in after account creation.");
        }

        return;
      }

      const { data: freshProfile } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", loginData.user.id)
        .single();

      onLogin(
        await buildLoginUser({
          authUser: loginData.user,
          profile: freshProfile || profilePayload,
          accessToken: loginData.session.access_token,
        })
      );
    } catch (err) {
      setError(err.message || "Unable to create account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ait-login-page">
      <div className="ait-login-shell">
        <div className="ait-login-left">
          <img src={logo} alt="AI Tutor" className="ait-login-logo" />

          <h1>Learn smarter with AI.</h1>

          <p>
            Personalized CBSE preparation with AI-powered lessons, quizzes,
            analytics, narration, and doubt solving. Class 5–10.
          </p>

          <div className="ait-feature-list">
            <div>
              <BookOpen size={24} strokeWidth={2.4} />
              <span>Personalized Lessons</span>
            </div>

            <div>
              <Brain size={24} strokeWidth={2.4} />
              <span>Smart Doubt Solving</span>
            </div>

            <div>
              <ClipboardList size={24} strokeWidth={2.4} />
              <span>Practice & Tests</span>
            </div>

            <div>
              <BarChart3 size={24} strokeWidth={2.4} />
              <span>Progress Analytics</span>
            </div>
          </div>
        </div>

        <div className="ait-login-right">
          <div className="ait-form-card">
            <h2>{isSignupMode ? "Create Parent Account" : "Welcome back"}</h2>

            <p>
              {isSignupMode
                ? "Create your parent account to begin."
                : "Sign in to continue learning."}
            </p>

            <form onSubmit={isSignupMode ? handleSignup : handleLogin}>
              {isSignupMode && (
                <div className="ait-input-row">
                  <span>🧑</span>

                  <input
                    type="text"
                    placeholder="Enter your full name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
              )}

              <div className="ait-input-row">
                <span>👤</span>

                <input
                  type="text"
                  placeholder="Username or email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="ait-input-row">
                <span>🔒</span>

                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "🙈" : "👁️"}
                </button>
              </div>

              {!isSignupMode && (
                <div className="ait-login-options">
                  <button
                    type="button"
                    onClick={handleForgotPassword}
                    disabled={loading}
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                className="ait-signin-btn"
                type="submit"
                disabled={loading}
              >
                {loading
                  ? isSignupMode
                    ? "Creating..."
                    : "Signing in..."
                  : isSignupMode
                  ? "Create Parent Account"
                  : "Sign in"}
              </button>

              {/* Google OAuth button — official Google button style */}
              <div style={{ margin: "16px 0", textAlign: "center", color: "var(--text-muted,#64748b)", fontSize: "0.82rem" }}>
                — or —
              </div>
              <button
                type="button"
                onClick={signInWithGoogle}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  padding: "11px 16px",
                  borderRadius: 10,
                  border: "1px solid #dadce0",
                  background: "#fff",
                  color: "#3c4043",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "'Google Sans', Roboto, Arial, sans-serif",
                  transition: "box-shadow 0.15s, background 0.15s",
                  boxShadow: "0 1px 3px rgba(0,0,0,.08)",
                }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,.18)"; e.currentTarget.style.background = "#f8f9fa"; }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,.08)"; e.currentTarget.style.background = "#fff"; }}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
                  <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
                </svg>
                Sign in with Google
              </button>

              <div className="ait-divider"></div>

              <div className="ait-create-account">
                {isSignupMode ? "Already have an account?" : "New here?"}

                <span
                  style={{ cursor: "pointer", marginLeft: 6 }}
                  onClick={() => {
                    if (!isSignupMode && onShowSignup) {
                      onShowSignup();
                    } else {
                      setIsSignupMode(!isSignupMode);
                    }
                  }}
                >
                  {isSignupMode ? "Sign in" : "Create an account"}
                </span>
              </div>
            </form>

            {error && <div className="error-box">{error}</div>}
            {infoMessage && <div className="info-box">{infoMessage}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;

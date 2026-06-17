import { useState } from "react";
import logo from "../assets/AITutorLogo1.png";

import { BookOpen, Brain, ClipboardList, BarChart3 } from "lucide-react";

import { supabase } from "../api/supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
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

  function buildLoginUser({ authUser, profile, accessToken }) {
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

      dailyTokenLimit: profile.daily_token_limit,
      monthlyTokenLimit: profile.monthly_token_limit,
      subscriptionPlan: profile.subscription_plan || "free",
      accountStatus: profile.account_status || "active",
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
        buildLoginUser({
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
    /** Send a Supabase password reset email without exposing whether the account exists. */
    setError("");
    setInfoMessage("");

    if (!username.trim()) {
      setError("Enter your username or email first, then request a reset link.");
      return;
    }

    setLoading(true);

    try {
      const resetEmail = await resolveLoginEmail(username);

      if (resetEmail) {
        await supabase.auth.resetPasswordForEmail(resetEmail, {
          redirectTo: PASSWORD_RESET_REDIRECT_URL,
        });
      }

      setInfoMessage(
        "If this account exists, a password reset link has been sent."
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
            "📧 Please confirm your email address first. Check your inbox for a confirmation link from LikhaPoha AI. Check your spam folder if you don't see it."
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
        buildLoginUser({
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
            Personalized CBSE + SOF Olympiad preparation with AI-powered
            lessons, quizzes, analytics, narration, and doubt solving.
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
                  <label>
                    <input type="checkbox" />
                    Remember me
                  </label>

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

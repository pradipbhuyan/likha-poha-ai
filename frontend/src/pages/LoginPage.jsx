import { useState } from "react";
import logo from "../assets/AITutorLogo1.png";

import { BookOpen, Brain, ClipboardList, BarChart3 } from "lucide-react";

import { supabase } from "../api/supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function LoginPage({ onLogin }) {
  /** Handles Supabase authentication and parent signup for the app entry point. */
  const [isSignupMode, setIsSignupMode] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function buildLoginUser({ authUser, profile, accessToken }) {
    /** Convert Supabase auth/profile rows into the app's normalized user object. */
    return {
      id: authUser.id,
      email: authUser.email,
      username: profile.username || authUser.email,
	      role: profile.role,
	      grade: profile.grade || "Grade 9",
	      parentId: profile.parent_id,
      familyId: profile.family_id,

      accessToken,

      accessCbse: !!profile.access_cbse,
      accessSofScience: !!profile.access_sof_science,
      accessSofMaths: !!profile.access_sof_maths,
      accessSofEnglish: !!profile.access_sof_english,

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

      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginEmail,
        password,
      });

      if (error) {
        setError(
          `Supabase login failed for ${loginEmail}: ${error.message}`
        );
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
        setError(error.message);
        return;
      }

      if (!data.user) {
        setError("Unable to create account.");
        return;
      }

      const familyId = crypto.randomUUID();

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

      const { data: loginData, error: loginError } =
        await supabase.auth.signInWithPassword({
          email: username,
          password,
        });

      if (loginError) {
        setError(loginError.message);
        return;
      }

      onLogin(
        buildLoginUser({
          authUser: loginData.user,
          profile: profilePayload,
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
                  placeholder="Enter username or email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="ait-input-row">
                <span>🔒</span>

                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter password"
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

                  <button type="button">Forgot password?</button>
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
                  style={{
                    cursor: "pointer",
                    marginLeft: 6,
                  }}
                  onClick={() => setIsSignupMode(!isSignupMode)}
                >
                  {isSignupMode ? "Sign in" : "Create a parent account"}
                </span>
              </div>
            </form>

            {error && <div className="error-box">{error}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;

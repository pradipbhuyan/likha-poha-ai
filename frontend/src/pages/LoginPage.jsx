import { useState } from "react";
import logo from "../assets/AITutorLogo.png";

import { BookOpen, Brain, ClipboardList, BarChart3 } from "lucide-react";

import { supabase } from "../api/supabaseClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

console.log(
    "VITE_API_BASE_URL =",
    import.meta.env.VITE_API_BASE_URL
  );

function LoginPage({ onLogin }) {
  const [isSignupMode, setIsSignupMode] = useState(false);

  const [username, setUsername] = useState("");

  const [password, setPassword] = useState("");

  const [fullName, setFullName] = useState("");

  const [error, setError] = useState("");

  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
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
          setError("Username not found.");
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
        setError(error.message);
        return;
      }

      const { data: profile, error: profileError } = await supabase
        .from("profiles")
        .select("id, email, username, role, parent_id")
        .eq("id", data.user.id)
        .single();

      if (profileError) {
        setError("Login successful, but profile role was not found.");

        return;
      }

      onLogin({
        id: data.user.id,
        email: data.user.email,
        username: profile.username || data.user.email,
        role: profile.role,
        parentId: profile.parent_id,
        accessToken: data.session.access_token,
      });
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSignup(e) {
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
  
      onLogin({
        id: loginData.user.id,
        email: loginData.user.email,
        username: fullName,
        role: "parent",
        parentId: null,
        accessToken: loginData.session.access_token,
      });
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
                  type="password"
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                <span>👁️</span>
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

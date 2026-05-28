import { useState } from "react";
import logo from "../assets/AITutorLogo.png";
import { BookOpen, Brain, ClipboardList, BarChart3 } from "lucide-react";
import { supabase } from "../api/supabaseClient";

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();
  
    setError("");
    setLoading(true);
  
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: username,
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
            <h2>Welcome back</h2>
            <p>Sign in to continue learning.</p>

            <form onSubmit={handleLogin}>
              <div className="ait-input-row">
                <span>👤</span>
                <input
                  type="email"
                  placeholder="Enter email"
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

              <div className="ait-login-options">
                <label>
                  <input type="checkbox" />
                  Remember me
                </label>

                <button type="button">Forgot password?</button>
              </div>

              <button
                className="ait-signin-btn"
                type="submit"
                disabled={loading}
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>

              <div className="ait-divider"></div>

              <div className="ait-create-account">
                New here? <span>Create an account</span>
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
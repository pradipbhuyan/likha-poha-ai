import { useState } from "react";
import { login } from "../api/auth";
import logo from "../assets/AITutorLogo.png";

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
      const result = await login(username, password);

      if (!result.success) {
        setError(result.message || "Invalid username or password");
      } else {
        onLogin(result);
      }
    } catch {
      setError("Login failed. Check backend is running.");
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
            Personalized CBSE + SOF Olympiad preparation with AI-powered lessons,
            quizzes, analytics, narration, and doubt solving.
          </p>

          <div className="ait-feature-list">
            <div>📖 Personalized Lessons</div>
            <div>❓ Smart Doubt Solving</div>
            <div>🧪 Practice & Tests</div>
            <div>📊 Progress Analytics</div>
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
                  type="text"
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="ait-input-row">
                <span>🔒</span>
                <input
                  type="password"
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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

              <button className="ait-signin-btn" type="submit" disabled={loading}>
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
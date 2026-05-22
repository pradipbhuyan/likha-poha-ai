import { useState } from "react";
import { login } from "../api/auth";


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
    <div className="login-page-premium">
      <div className="login-hero">
        <div className="brand-badge">AI Tutor Platform</div>

        <h1>
          Learn CBSE + SOF with your personal AI tutor.
        </h1>

        <p>
          Lessons, doubts, quizzes, mock tests, analytics, narration, and RAG-powered textbook learning in one place.
        </p>

        <div className="feature-grid">
          <div>📖 AI Lessons</div>
          <div>❓ Doubt Solver</div>
          <div>🧪 Mock Tests</div>
          <div>📊 Analytics</div>
          <div>🔊 Narration</div>
          <div>📚 RAG Textbooks</div>
        </div>
      </div>

      <div className="login-panel">
        <div className="login-card-premium">
          <div className="logo-orb">📚</div>

          <h2>Welcome back</h2>
          <p className="login-subtitle">
            Sign in to continue learning.
          </p>

          <form onSubmit={handleLogin}>
            <label>
              Username
              <input
                type="text"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <label>
              Password
              <input
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <button type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {error && <div className="error-box">{error}</div>}
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
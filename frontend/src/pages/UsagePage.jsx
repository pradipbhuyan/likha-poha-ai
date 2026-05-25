import { useEffect, useState } from "react";
import { getUsageSummary } from "../api/usage";

import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

function UsagePage() {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUsage() {
      try {
        const data = await getUsageSummary();
        setUsage(data);
      } finally {
        setLoading(false);
      }
    }

    loadUsage();
  }, []);

  if (loading) return <p>Loading usage...</p>;

  const userCostData = usage?.by_user || [];
  const featureCostData = usage?.by_feature || [];

  return (
    <div className="usage-page premium-page premium-usage-page">
      <section className="premium-section premium-usage-hero">
        <div className="premium-header">
          <p className="eyebrow">Admin Operations</p>
          <h2>💸 AI Usage Dashboard</h2>
          <p>
            Monitor AI cost, tokens, image usage, feature consumption, and
            operational alerts across users.
          </p>
        </div>

        <div className="premium-usage-ops-card">
          <span>🛡️</span>
          <div>
            <strong>{usage?.alerts?.length || 0}</strong>
            <p>active operational alerts</p>
          </div>
        </div>
      </section>

      <section className="premium-grid premium-grid-4 premium-usage-stats">
        <div className="premium-card premium-glow-card glow-blue">
          <strong>Total Cost</strong>
          <p>${Number(usage?.totals?.total_cost || 0).toFixed(6)}</p>
        </div>

        <div className="premium-card premium-glow-card glow-purple">
          <strong>Total Tokens</strong>
          <p>{usage?.totals?.total_tokens || 0}</p>
        </div>

        <div className="premium-card premium-glow-card glow-green">
          <strong>Requests</strong>
          <p>{usage?.totals?.requests || 0}</p>
        </div>

        <div className="premium-card premium-glow-card glow-red">
          <strong>Images</strong>
          <p>{usage?.totals?.total_images || 0}</p>
        </div>
      </section>

      {usage?.alerts?.length > 0 && (
        <section className="premium-section premium-usage-alert-section">
          <div className="premium-header">
            <h3>⚠️ Usage Alerts</h3>
            <p>Review cost spikes, high image usage, or unusual token volume.</p>
          </div>

          <div className="usage-alerts premium-usage-alerts">
            {usage.alerts.map((alert, index) => (
              <div key={index} className={`usage-alert ${alert.level}`}>
                ⚠️ {alert.message}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="usage-chart-grid premium-usage-chart-grid">
        <div className="dashboard-chart-card premium-card premium-chart-card">
          <div className="section-heading-row">
            <div>
              <h3>💰 Cost by User</h3>
              <p>Estimated AI spend grouped by user.</p>
            </div>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={userCostData}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="username" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  cursor={{ fill: "rgba(59, 130, 246, 0.08)" }}
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "14px",
                    color: "#f8fafc",
                  }}
                  labelStyle={{ color: "#f8fafc" }}
                  itemStyle={{ color: "#93c5fd" }}
                />
                <Bar
                  dataKey="total_cost"
                  fill="#3b82f6"
                  radius={[10, 10, 0, 0]}
                  activeBar={{ fill: "#60a5fa" }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="dashboard-chart-card premium-card premium-chart-card">
          <div className="section-heading-row">
            <div>
              <h3>⚙️ Cost by Feature</h3>
              <p>Which AI features are consuming the most cost.</p>
            </div>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={featureCostData}
                  dataKey="total_cost"
                  nameKey="feature"
                  outerRadius={95}
                  fill="#3b82f6"
                  label
                />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "14px",
                    color: "#f8fafc",
                  }}
                  labelStyle={{ color: "#f8fafc" }}
                  itemStyle={{ color: "#93c5fd" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="premium-usage-detail-grid">
        <div className="premium-section premium-usage-list">
          <div className="premium-header">
            <h3>👤 Usage by User</h3>
            <p>Per-user requests, tokens, and estimated cost.</p>
          </div>

          {(usage?.by_user || []).map((item) => (
            <div key={item.username} className="premium-usage-row">
              <div>
                <strong>{item.username}</strong>
                <p>Requests: {item.requests}</p>
              </div>

              <div>
                <span>{item.total_tokens}</span>
                <small>tokens</small>
              </div>

              <div>
                <span>${Number(item.total_cost || 0).toFixed(6)}</span>
                <small>cost</small>
              </div>
            </div>
          ))}
        </div>

        <div className="premium-section premium-usage-list">
          <div className="premium-header">
            <h3>🧩 Usage by Feature</h3>
            <p>Feature-level AI usage breakdown.</p>
          </div>

          {(usage?.by_feature || []).map((item) => (
            <div key={item.feature} className="premium-usage-row">
              <div>
                <strong>{item.feature}</strong>
                <p>Requests: {item.requests}</p>
              </div>

              <div>
                <span>{item.total_tokens}</span>
                <small>tokens</small>
              </div>

              <div>
                <span>${Number(item.total_cost || 0).toFixed(6)}</span>
                <small>cost</small>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="premium-section premium-usage-logs">
        <div className="premium-header">
          <h3>🕘 Recent Usage Logs</h3>
          <p>Most recent AI calls recorded by the platform.</p>
        </div>

        <div className="premium-usage-log-list">
          {(usage?.recent_logs || []).map((item) => (
            <div key={item.id} className="premium-usage-log-row">
              <div>
                <strong>
                  {item.username} — {item.feature}
                </strong>
                <p>Model: {item.model || "N/A"}</p>
              </div>

              <div>
                <span>{item.total_tokens}</span>
                <small>tokens</small>
              </div>

              <div>
                <span>${Number(item.estimated_cost || 0).toFixed(6)}</span>
                <small>cost</small>
              </div>

              <time>{(item.created_at || "").slice(0, 19)}</time>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default UsagePage;

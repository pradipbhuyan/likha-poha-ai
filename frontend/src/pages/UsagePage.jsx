import { useEffect, useState } from "react";
import { getUsageSummary } from "../api/usage";

import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
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
    <div className="usage-page">
      <div className="result-grid">
        <div>
          <strong>Total Cost</strong>
          <p>${usage?.totals?.total_cost || 0}</p>
        </div>

        <div>
          <strong>Total Tokens</strong>
          <p>{usage?.totals?.total_tokens || 0}</p>
        </div>

        <div>
          <strong>Requests</strong>
          <p>{usage?.totals?.requests || 0}</p>
        </div>

        <div>
          <strong>Images</strong>
          <p>{usage?.totals?.total_images || 0}</p>
        </div>
      </div>

      {usage?.alerts?.length > 0 && (
        <div className="usage-alerts">
          {usage.alerts.map((alert, index) => (
            <div key={index} className={`usage-alert ${alert.level}`}>
              ⚠️ {alert.message}
            </div>
          ))}
        </div>
      )}

      <div className="usage-chart-grid">
        <div className="dashboard-chart-card">
          <h3>💰 Cost by User</h3>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={userCostData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="username" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_cost" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="dashboard-chart-card">
          <h3>⚙️ Cost by Feature</h3>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={featureCostData}
                  dataKey="total_cost"
                  nameKey="feature"
                  outerRadius={95}
                  label
                />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Usage by User</h3>

        {(usage?.by_user || []).map((item) => (
          <div key={item.username} className="question-card">
            <strong>{item.username}</strong>
            <p>Requests: {item.requests}</p>
            <p>Tokens: {item.total_tokens}</p>
            <p>Cost: ${Number(item.total_cost || 0).toFixed(6)}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Usage by Feature</h3>

        {(usage?.by_feature || []).map((item) => (
          <div key={item.feature} className="question-card">
            <strong>{item.feature}</strong>
            <p>Requests: {item.requests}</p>
            <p>Tokens: {item.total_tokens}</p>
            <p>Cost: ${Number(item.total_cost || 0).toFixed(6)}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Recent Usage Logs</h3>

        {(usage?.recent_logs || []).map((item) => (
          <div key={item.id} className="question-card">
            <strong>
              {item.username} — {item.feature}
            </strong>
            <p>Model: {item.model || "N/A"}</p>
            <p>Tokens: {item.total_tokens}</p>
            <p>Cost: ${Number(item.estimated_cost || 0).toFixed(6)}</p>
            <p>{(item.created_at || "").slice(0, 19)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default UsagePage;

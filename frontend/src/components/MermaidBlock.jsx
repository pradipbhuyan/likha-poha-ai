import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  theme: "base",
  themeVariables: {
    background: "transparent",
    primaryColor: "#eff6ff",
    primaryTextColor: "#0f172a",
    primaryBorderColor: "#60a5fa",
    lineColor: "#2563eb",
    secondaryColor: "#f8fafc",
    tertiaryColor: "#dbeafe",
    fontFamily: "Inter, system-ui, sans-serif",
  },
});

function MermaidBlock({ chart }) {
  const ref = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function renderChart() {
      if (!ref.current || !chart) return;

      try {
        setError("");

        const id = `mermaid-${crypto.randomUUID()}`;
        const { svg } = await mermaid.render(id, chart);

        ref.current.innerHTML = svg;
      } catch (err) {
        console.error("Mermaid render failed", err);
        setError("Could not render diagram.");
      }
    }

    renderChart();
  }, [chart]);

  return (
    <div className="mermaid-card">
      <div className="mermaid-card-header">
        <span>📊 Diagram</span>
      </div>

      {error ? (
        <div className="mermaid-error">{error}</div>
      ) : (
        <div ref={ref} className="mermaid-box" />
      )}
    </div>
  );
}

export default MermaidBlock;
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

function cleanMermaidChart(input) {
  /** Normalize AI-generated Mermaid syntax before handing it to the renderer. */
  if (!input) return "";

  let chart = String(input)
    .replace(/```mermaid/g, "")
    .replace(/```/g, "")
    .trim();

  chart = chart.replace(/graph TD(?!\n)/g, "graph TD\n");
  chart = chart.replace(/graph LR(?!\n)/g, "graph LR\n");
  chart = chart.replace(/\]\s*([A-Za-z0-9_]+)\[/g, "]\n$1[");
  chart = chart.replace(/\)\s*([A-Za-z0-9_]+)\[/g, ")\n$1[");

  chart = chart.replace(
    /^([A-Za-z0-9_]+)\[([^\]]+)\]$/gm,
    (_, nodeId, label) => {
      const safeLabel = label.replace(/"/g, "'");
      return `${nodeId}["${safeLabel}"]`;
    }
  );

  chart = chart
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n");

  return chart;
}

function MermaidBlock({ chart }) {
  /** Renders a Mermaid diagram and falls back to text if the diagram cannot be parsed. */
  const ref = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function renderChart() {
      /** Render the current Mermaid chart into an isolated SVG container. */
      if (!ref.current || !chart) return;

      try {
        setError("");
        ref.current.innerHTML = "";

        const cleanedChart = cleanMermaidChart(chart);
        const id = `mermaid-${crypto.randomUUID()}`;
        const { svg } = await mermaid.render(id, cleanedChart);

        ref.current.innerHTML = svg;
      } catch (err) {
        console.error("Mermaid render failed", err);
        setError("Could not render diagram. Showing text version instead.");
      }
    }

    renderChart();
  }, [chart]);

  const cleanedChart = cleanMermaidChart(chart);

  return (
    <div className="mermaid-card">
      <div className="mermaid-card-header">
        <span>📊 Diagram</span>
      </div>

      {error ? (
        <div className="mermaid-error">
          <p>{error}</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>{cleanedChart}</pre>
        </div>
      ) : (
        <div ref={ref} className="mermaid-box" />
      )}
    </div>
  );
}

export default MermaidBlock;

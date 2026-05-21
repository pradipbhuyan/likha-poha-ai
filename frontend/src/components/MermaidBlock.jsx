import { useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
});

function MermaidBlock({ chart }) {
  const ref = useRef(null);

  useEffect(() => {
    async function renderChart() {
      if (!ref.current || !chart) return;

      try {
        const id = "mermaid-" + Math.random().toString(36).slice(2);
        const { svg } = await mermaid.render(id, chart);
        ref.current.innerHTML = svg;
      } catch {
        ref.current.innerHTML = "<p>Could not render diagram.</p>";
      }
    }

    renderChart();
  }, [chart]);

  return <div ref={ref} className="mermaid-box" />;
}

export default MermaidBlock;
import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  flowchart: {
    htmlLabels: false,
    useMaxWidth: false,
    nodeSpacing: 70,
    rankSpacing: 70,
    padding: 18,
  },
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

function cleanMermaidLabel(label) {
  /** Convert any old HTML label markup back to plain text for SVG-based Mermaid labels. */
  return String(label || "")
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .replace(/"/g, "'")
    .trim();
}

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
    /^([A-Za-z0-9_]+)\["([^"]+)"\]$/gm,
    (_, nodeId, label) => {
      const safeLabel = cleanMermaidLabel(label);
      return `${nodeId}["${safeLabel}"]`;
    }
  );

  chart = chart.replace(
    /^([A-Za-z0-9_]+)\[(?!")([^\]]+)\]$/gm,
    (_, nodeId, label) => {
      const safeLabel = cleanMermaidLabel(label);
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

function parseSimpleNode(rawNode, labels) {
  /** Extract a Mermaid node id and label from simple box/circle node syntax. */
  const nodeText = String(rawNode || "").trim().replace(/;$/, "");
  const match = nodeText.match(
    /^([A-Za-z0-9_]+)(?:\[\["([^"]+)"\]\]|\["([^"]+)"\]|\[([^\]]+)\]|\(\("([^"]+)"\)\)|\("([^"]+)"\)|\(([^)]+)\)|\{\{([^}]+)\}\}|>\s*([^\]]+)\]|\[\/(.+)\/\])?$/
  );

  if (!match) return null;

  const [
    ,
    id,
    doubleBoxLabel,
    quotedLabel,
    boxLabel,
    doubleCircleLabel,
    quotedCircleLabel,
    circleLabel,
    hexLabel,
    flagLabel,
    slantedLabel,
  ] = match;
  const explicitLabel =
    doubleBoxLabel ||
    quotedLabel ||
    boxLabel ||
    doubleCircleLabel ||
    quotedCircleLabel ||
    circleLabel ||
    hexLabel ||
    flagLabel ||
    slantedLabel;

  if (explicitLabel) {
    labels.set(id, cleanMermaidLabel(explicitLabel));
  } else if (!labels.has(id)) {
    labels.set(id, id);
  }

  return id;
}

function buildFlowchartLevels(nodeIds, edges) {
  /** Build readable top-to-bottom rows for branching or merging educational diagrams. */
  const incomingByNode = new Map();
  const outgoingByNode = new Map();

  nodeIds.forEach((nodeId) => {
    incomingByNode.set(nodeId, []);
    outgoingByNode.set(nodeId, []);
  });

  edges.forEach(({ from, to }) => {
    outgoingByNode.set(from, [...(outgoingByNode.get(from) || []), to]);
    incomingByNode.set(to, [...(incomingByNode.get(to) || []), from]);
  });

  const memo = new Map();
  const visiting = new Set();

  function getDepth(nodeId) {
    /** Calculate a stable level by walking backwards through incoming edges. */
    if (memo.has(nodeId)) return memo.get(nodeId);
    if (visiting.has(nodeId)) return 0;

    visiting.add(nodeId);

    const incoming = incomingByNode.get(nodeId) || [];
    const depth = incoming.length
      ? Math.max(...incoming.map((sourceId) => getDepth(sourceId))) + 1
      : 0;

    visiting.delete(nodeId);
    memo.set(nodeId, depth);

    return depth;
  }

  const levelMap = new Map();

  nodeIds.forEach((nodeId) => {
    const depth = getDepth(nodeId);
    levelMap.set(depth, [...(levelMap.get(depth) || []), nodeId]);
  });

  return [...levelMap.entries()]
    .sort(([leftDepth], [rightDepth]) => leftDepth - rightDepth)
    .map(([, ids]) => ids);
}

function parseSimpleFlowchart(chartText) {
  /** Parse simple AI-generated box-and-arrow Mermaid into a safer HTML renderer model. */
  const lines = String(chartText || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const header = lines[0] || "";
  const directionMatch = header.match(/^graph\s+(TD|TB|BT|LR|RL)$/i);

  if (!directionMatch) return null;

  const labels = new Map();
  const edges = [];

  for (const line of lines.slice(1)) {
    if (/^(class|classDef|style|subgraph|end|click)\b/i.test(line)) {
      return null;
    }

    if (!/(-->|-.->|==>)/.test(line) || line.includes("|")) {
      const nodeId = parseSimpleNode(line, labels);
      if (!nodeId) return null;
      continue;
    }

    const parts = line.split(/\s*(?:-->|-.->|==>)\s*/).filter(Boolean);

    if (parts.length < 2) return null;

    for (let index = 0; index < parts.length - 1; index += 1) {
      const from = parseSimpleNode(parts[index], labels);
      const to = parseSimpleNode(parts[index + 1], labels);

      if (!from || !to) return null;

      edges.push({ from, to });
    }
  }

  if (!edges.length) return null;

  const outgoing = new Map();
  const incoming = new Map();
  edges.forEach(({ from, to }) => {
    outgoing.set(from, [...(outgoing.get(from) || []), to]);
    incoming.set(to, (incoming.get(to) || 0) + 1);
    if (!incoming.has(from)) incoming.set(from, incoming.get(from) || 0);
  });

  const nodeIds = [...new Set(edges.flatMap(({ from, to }) => [from, to]))];
  const hasBranchingOrMerging =
    [...outgoing.values()].some((targets) => targets.length > 1) ||
    [...incoming.values()].some((count) => count > 1);

  if (hasBranchingOrMerging) {
    return {
      direction: directionMatch[1].toUpperCase(),
      layout: "levels",
      levels: buildFlowchartLevels(nodeIds, edges).map((level) =>
        level.map((nodeId) => ({
          id: nodeId,
          label: labels.get(nodeId) || nodeId,
        }))
      ),
    };
  }

  const startNodes = nodeIds.filter((nodeId) => !incoming.get(nodeId));
  const chainStarts = startNodes.length ? startNodes : [edges[0].from];
  const chains = chainStarts.map((startNode) => {
    const chain = [];
    const visited = new Set();
    let currentNode = startNode;

    while (currentNode && !visited.has(currentNode)) {
      visited.add(currentNode);
      chain.push({
        id: currentNode,
        label: labels.get(currentNode) || currentNode,
      });
      currentNode = outgoing.get(currentNode)?.[0];
    }

    return chain;
  });

  return {
    direction: directionMatch[1].toUpperCase(),
    layout: "chains",
    chains,
  };
}

function SimpleFlowchart({ graph }) {
  /** Render simple flowcharts as HTML so labels wrap naturally without SVG clipping. */
  return (
    <div
      className={`simple-flowchart simple-flowchart-${graph.layout}`}
      data-direction={graph.direction}
    >
      {graph.layout === "levels"
        ? graph.levels.map((level, levelIndex) => (
            <div className="simple-flowchart-level" key={`level-${levelIndex}`}>
              <div className="simple-flowchart-level-nodes">
                {level.map((node) => (
                  <div className="simple-flowchart-node" key={node.id}>
                    {node.label}
                  </div>
                ))}
              </div>
              {levelIndex < graph.levels.length - 1 && (
                <div className="simple-flowchart-level-arrow" aria-hidden="true">
                  ↓
                </div>
              )}
            </div>
          ))
        : graph.chains.map((chain, chainIndex) => (
            <div className="simple-flowchart-chain" key={`chain-${chainIndex}`}>
              {chain.map((node, nodeIndex) => (
                <div className="simple-flowchart-step" key={node.id}>
                  <div className="simple-flowchart-node">{node.label}</div>
                  {nodeIndex < chain.length - 1 && (
                    <div className="simple-flowchart-arrow" aria-hidden="true" />
                  )}
                </div>
              ))}
            </div>
          ))}
    </div>
  );
}

function MermaidBlock({ chart }) {
  /** Renders a Mermaid diagram and falls back to text if the diagram cannot be parsed. */
  const ref = useRef(null);
  const [error, setError] = useState("");
  const cleanedChart = cleanMermaidChart(chart);
  const simpleGraph = parseSimpleFlowchart(cleanedChart);

  useEffect(() => {
    async function renderChart() {
      /** Render the current Mermaid chart into an isolated SVG container. */
      if (!ref.current || !chart || simpleGraph) return;

      try {
        setError("");
        ref.current.innerHTML = "";

        const id = `mermaid-${crypto.randomUUID()}`;
        const { svg } = await mermaid.render(id, cleanedChart);

        ref.current.innerHTML = svg;
      } catch (err) {
        console.error("Mermaid render failed", err);
        setError("Could not render diagram. Showing text version instead.");
      }
    }

    renderChart();
  }, [chart, cleanedChart, simpleGraph]);

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
      ) : simpleGraph ? (
        <SimpleFlowchart graph={simpleGraph} />
      ) : (
        <div ref={ref} className="mermaid-box" />
      )}
    </div>
  );
}

export default MermaidBlock;

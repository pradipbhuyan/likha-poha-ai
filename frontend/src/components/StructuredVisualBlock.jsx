const VISUAL_TYPES = new Set(["flow", "steps", "cycle", "compare"]);

function cleanText(value) {
  /** Normalize visual labels without changing their meaning. */
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

function isSafeLabel(value, maxLength = 70) {
  /** Keep generated visual text complete, short, and HTML-safe. */
  const text = cleanText(value);
  return text.length >= 2 && text.length <= maxLength && !/[<>]/.test(text);
}

function parseVisual(raw) {
  /** Parse a model-generated visual-json block into validated display data. */
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function validateStructuredVisual(raw) {
  /** Accept only constrained visual structures that the UI can render reliably. */
  const visual = typeof raw === "string" ? parseVisual(raw) : raw;

  if (!visual || !VISUAL_TYPES.has(visual.type)) {
    return null;
  }

  const title = cleanText(visual.title);

  if (!isSafeLabel(title, 80)) {
    return null;
  }

  if (visual.type === "compare") {
    if (
      !Array.isArray(visual.columns) ||
      visual.columns.length !== 2 ||
      !visual.columns.every((column) => isSafeLabel(column, 45)) ||
      !Array.isArray(visual.rows) ||
      visual.rows.length < 2 ||
      visual.rows.length > 5
    ) {
      return null;
    }

    const rows = visual.rows
      .map((row) => {
        if (!Array.isArray(row) || row.length !== 2) {
          return null;
        }

        const cells = row.map(cleanText);
        return cells.every((cell) => isSafeLabel(cell, 70)) ? cells : null;
      })
      .filter(Boolean);

    if (rows.length !== visual.rows.length) {
      return null;
    }

    return {
      type: visual.type,
      title,
      columns: visual.columns.map(cleanText),
      rows,
    };
  }

  if (
    !Array.isArray(visual.items) ||
    visual.items.length < 2 ||
    visual.items.length > 6 ||
    !visual.items.every((item) => isSafeLabel(item, 70))
  ) {
    return null;
  }

  const note = cleanText(visual.note);

  return {
    type: visual.type,
    title,
    items: visual.items.map(cleanText),
    note: isSafeLabel(note, 120) ? note : "",
  };
}

function FlowVisual({ visual }) {
  /** Render a vertical flow that wraps text instead of clipping it. */
  return (
    <div className="structured-flow" aria-label={visual.title}>
      {visual.items.map((item, index) => (
        <div key={`${item}-${index}`} className="structured-flow-row">
          <div className="structured-flow-node">{item}</div>
          {index < visual.items.length - 1 && (
            <div className="structured-flow-arrow" aria-hidden="true">
              ↓
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function StepsVisual({ visual }) {
  /** Render ordered steps with explicit numbering for maths/science methods. */
  return (
    <ol className="structured-steps">
      {visual.items.map((item, index) => (
        <li key={`${item}-${index}`}>
          <span>{index + 1}</span>
          <p>{item}</p>
        </li>
      ))}
    </ol>
  );
}

function CycleVisual({ visual }) {
  /** Render cycle items as repeatable cards without implying exact geometry. */
  return (
    <div className="structured-cycle">
      {visual.items.map((item, index) => (
        <div key={`${item}-${index}`} className="structured-cycle-node">
          <span>{index + 1}</span>
          <p>{item}</p>
        </div>
      ))}
    </div>
  );
}

function CompareVisual({ visual }) {
  /** Render comparisons as real HTML tables for reliable wrapping. */
  return (
    <div className="structured-compare-wrap">
      <table className="structured-compare">
        <thead>
          <tr>
            {visual.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visual.rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell) => (
                <td key={cell}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StructuredVisualBlock({ raw }) {
  /** Show only validated structured visuals; hide unsafe or uncertain output. */
  const visual = validateStructuredVisual(raw);

  if (!visual) {
    return null;
  }

  return (
    <section className="structured-visual-card">
      <div className="structured-visual-header">
        <span>Visual aid</span>
        <strong>{visual.title}</strong>
      </div>

      {visual.type === "flow" && <FlowVisual visual={visual} />}
      {visual.type === "steps" && <StepsVisual visual={visual} />}
      {visual.type === "cycle" && <CycleVisual visual={visual} />}
      {visual.type === "compare" && <CompareVisual visual={visual} />}

      {visual.note && <p className="structured-visual-note">{visual.note}</p>}
    </section>
  );
}

export default StructuredVisualBlock;

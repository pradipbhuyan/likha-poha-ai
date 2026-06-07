import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import StructuredVisualBlock, {
  validateStructuredVisual,
} from "../components/StructuredVisualBlock";

describe("StructuredVisualBlock", () => {
  test("renders a valid flow visual", () => {
    const raw = JSON.stringify({
      type: "flow",
      title: "Dalton theory logic",
      items: [
        "Matter is made of atoms",
        "Atoms combine in fixed ratios",
        "Chemical laws are explained",
      ],
      note: "Use this as a memory path.",
    });

    render(<StructuredVisualBlock raw={raw} />);

    expect(screen.getByText("Visual aid")).toBeInTheDocument();
    expect(screen.getByText("Dalton theory logic")).toBeInTheDocument();
    expect(screen.getByText("Matter is made of atoms")).toBeInTheDocument();
    expect(screen.getByText("Use this as a memory path.")).toBeInTheDocument();
  });

  test("rejects invalid JSON", () => {
    const { container } = render(<StructuredVisualBlock raw="not json" />);

    expect(container).toBeEmptyDOMElement();
  });

  test("rejects labels that are too long to render safely", () => {
    const raw = JSON.stringify({
      type: "flow",
      title: "Unsafe long labels",
      items: [
        "This label is intentionally far too long because it would create the same clipped visual problem that confused students earlier",
        "Short label",
      ],
    });

    expect(validateStructuredVisual(raw)).toBeNull();
  });

  test("renders a valid comparison as a table", () => {
    const raw = JSON.stringify({
      type: "compare",
      title: "Atom and molecule",
      columns: ["Atom", "Molecule"],
      rows: [
        ["Smallest unit of element", "Group of atoms"],
        ["May exist alone", "Can be same or different atoms"],
      ],
    });

    render(<StructuredVisualBlock raw={raw} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Atom and molecule")).toBeInTheDocument();
    expect(screen.getByText("Group of atoms")).toBeInTheDocument();
  });
});

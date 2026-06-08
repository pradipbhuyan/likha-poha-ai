import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import LessonSections from "../components/LessonSections";

describe("LessonSections", () => {
  test("renders labelled quick-check questions only through answer controls", () => {
    const lesson = `
1. Simple explanation

\`\`\`visual-json
{"type":"flow","title":"Golgi Apparatus Function","items":["Receives proteins and lipids from ER","Modifies and sorts molecules","Packages into vesicles","Transports molecules to destinations"],"note":"Golgi apparatus is the cell packaging and shipping centre."}
\`\`\`

Quick check question:
What is the main role of the Golgi apparatus in a cell?
`;

    render(
      <LessonSections lesson={lesson} onEvaluateQuestion={vi.fn()} />
    );

    expect(screen.getByText("Golgi Apparatus Function")).toBeInTheDocument();
    expect(
      screen.getByText("Golgi apparatus is the cell packaging and shipping centre.")
    ).toBeInTheDocument();
    expect(screen.queryByText("Quick check question:")).not.toBeInTheDocument();
    expect(screen.getByText("Want to try this question?")).toBeInTheDocument();
    expect(
      screen.getByText("What is the main role of the Golgi apparatus in a cell?")
    ).toBeInTheDocument();

    fireEvent.click(screen.getByText("Leave for thinking"));

    expect(
      screen.getByText("Saved as a thinking prompt. No answer will be checked.")
    ).toBeInTheDocument();
  });
});

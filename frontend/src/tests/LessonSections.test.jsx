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

  test("Grade 5 Quick Check with MCQ format renders as a flip card, hiding the answer until clicked", () => {
    const lesson = `
## Quick check question

Which of the following is an irrational number?

A) 0.5
B) √2
C) 22/7
D) 1.25

Answer: B

Explanation: Root 2 is irrational because it cannot be expressed as p by q.
`;

    render(
      <LessonSections lesson={lesson} onEvaluateQuestion={vi.fn()} grade="Grade 5" />
    );

    const card = screen.getByRole("button", { name: /tap the card to reveal the answer/i });
    expect(card).toHaveAttribute("aria-pressed", "false");
    expect(card.className).not.toMatch(/is-flipped/);

    // Front shows the question and all options; the old type-and-evaluate flow is gone
    expect(
      screen.getByText("Which of the following is an irrational number?")
    ).toBeInTheDocument();
    expect(screen.getAllByText("√2").length).toBeGreaterThan(0);
    expect(screen.queryByText("Answer and evaluate")).not.toBeInTheDocument();
    expect(screen.queryByText("Leave for thinking")).not.toBeInTheDocument();

    fireEvent.click(card);

    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(card.className).toMatch(/is-flipped/);
    expect(screen.getByText(/Root 2 is irrational/)).toBeInTheDocument();

    fireEvent.click(card);
    expect(card).toHaveAttribute("aria-pressed", "false");
    expect(card.className).not.toMatch(/is-flipped/);
  });

  test("non-Grade-5 lessons keep the existing type-and-evaluate Quick Check box for the same MCQ content", () => {
    const lesson = `
## Quick check question

Which of the following is an irrational number?

A) 0.5
B) √2
C) 22/7
D) 1.25

Answer: B

Explanation: Root 2 is irrational because it cannot be expressed as p by q.
`;

    render(
      <LessonSections lesson={lesson} onEvaluateQuestion={vi.fn()} grade="Grade 9" />
    );

    expect(screen.getByText("Want to try this question?")).toBeInTheDocument();
    expect(screen.getByText("Answer and evaluate")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /tap the card to reveal the answer/i })
    ).not.toBeInTheDocument();
  });

  test("Grade 5 falls back to the standard Quick Check box when content isn't MCQ-formatted", () => {
    const lesson = `
1. Simple explanation

Quick check question:
What is the main role of the Golgi apparatus in a cell?
`;

    render(
      <LessonSections lesson={lesson} onEvaluateQuestion={vi.fn()} grade="Grade 5" />
    );

    expect(screen.getByText("Want to try this question?")).toBeInTheDocument();
    expect(
      screen.getByText("What is the main role of the Golgi apparatus in a cell?")
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /tap the card to reveal the answer/i })
    ).not.toBeInTheDocument();
  });
});

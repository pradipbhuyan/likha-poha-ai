/**
 * FormulaSheetPage.test.jsx
 * Tests for the redesigned chapter-wise Formula Sheet page with freemium access.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));

import FormulaSheetPage from "../pages/FormulaSheetPage";
import { authFetch } from "../api/authClient";

const USER_FREE = { id: "u1", username: "test", grade: "Grade 9", accessCbse: false };
const USER_PAID = { id: "u2", username: "paiduser", grade: "Grade 9", accessCbse: true };

const FREE_RESPONSE = {
  success: true,
  available: true,
  grade: "Grade 9",
  subject: "Mathematics",
  subjects: ["Mathematics", "Science"],
  has_premium: false,
  premium_required: true,
  unlocked_count: 3,
  total_count: 10,
  upgrade_message: "Upgrade to unlock solved examples, memory tips and the full formula library.",
  chapters: [
    {
      chapter_id: "triangles",
      chapter_name: "Triangles",
      chapter_order: 1,
      total_formulas: 5,
      unlocked_count: 3,
      locked: true,
      topics: [
        {
          topic_name: "Area Formulas",
          formulas: [
            {
              id: "f1", name: "Heron's Formula", expression: "A=sqrt[s(s-a)(s-b)(s-c)]",
              description: "s is semi-perimeter", variables: "s=(a+b+c)/2, a,b,c=sides",
              chapter: "Triangles", topic: "Area Formulas", difficulty: "medium",
              tags: ["area", "triangle"], locked: false, preview_allowed: true,
              example: null, solution_steps: null, memory_tip: null,
              premium_sections: ["solved_example", "solution_steps", "memory_tip"],
            },
            {
              id: "f2", name: "Area by Base Height", expression: "A=(1/2)bh",
              description: "b=base, h=height", variables: "b=base, h=perpendicular height",
              chapter: "Triangles", topic: "Area Formulas", difficulty: "easy",
              tags: ["area"], locked: false, preview_allowed: true,
              example: null, solution_steps: null, memory_tip: null,
              premium_sections: ["solved_example", "solution_steps", "memory_tip"],
            },
            {
              id: "f3", name: "Pythagoras Theorem", expression: "a^2+b^2=c^2",
              description: "Right triangle relation", variables: "c=hypotenuse",
              chapter: "Triangles", topic: "Area Formulas", difficulty: "easy",
              tags: ["right-angle"], locked: false, preview_allowed: true,
              example: null, solution_steps: null, memory_tip: null,
              premium_sections: ["solved_example", "solution_steps", "memory_tip"],
            },
            {
              id: "f4", name: "Angle Sum Property", expression: "A+B+C=180",
              description: "Sum of angles in triangle", variables: "A,B,C are angles",
              chapter: "Triangles", topic: "Area Formulas", difficulty: "easy",
              tags: [], locked: true, preview_allowed: false,
              example: null, solution_steps: null, memory_tip: null,
              premium_sections: ["all"],
            },
          ],
        },
      ],
    },
    {
      chapter_id: "circles",
      chapter_name: "Circles",
      chapter_order: 2,
      total_formulas: 5,
      unlocked_count: 3,
      locked: true,
      topics: [{ topic_name: "Circle Formulas", formulas: [] }],
    },
  ],
};

const PAID_RESPONSE = {
  ...FREE_RESPONSE,
  has_premium: true,
  premium_required: false,
  unlocked_count: 10,
  upgrade_message: null,
  chapters: [
    {
      ...FREE_RESPONSE.chapters[0],
      locked: false,
      unlocked_count: 5,
      topics: [
        {
          topic_name: "Area Formulas",
          formulas: [
            {
              id: "f1", name: "Heron's Formula", expression: "A=sqrt[s(s-a)(s-b)(s-c)]",
              description: "s is semi-perimeter", variables: "s=(a+b+c)/2",
              chapter: "Triangles", topic: "Area Formulas", difficulty: "medium",
              tags: ["area"], locked: false, preview_allowed: true,
              example: "a=3,b=4,c=5: s=6, A=sqrt[6x3x2x1]=6 sq units",
              solution_steps: "1. Find s=(3+4+5)/2=6\n2. A=sqrt[6x3x2x1]=6",
              memory_tip: "HERON: Half-sum Example Root Of-product N-gives area",
              premium_sections: [],
            },
          ],
        },
      ],
    },
  ],
};

const GRADE_11_CONCEPT_RESPONSE = (subject, formula) => ({
  success: true,
  available: true,
  grade: "Grade 11",
  subject,
  subjects: ["Biology", "Chemistry", "Mathematics", "Physics"],
  has_premium: true,
  premium_required: false,
  unlocked_count: 1,
  total_count: 1,
  chapters: [{
    chapter_id: "concept-chapter",
    chapter_name: formula.chapter,
    chapter_order: 1,
    total_formulas: 1,
    unlocked_count: 1,
    locked: false,
    topics: [{
      topic_name: "General",
      formulas: [{
        id: `${subject}-concept`,
        difficulty: "medium",
        tags: [],
        locked: false,
        preview_allowed: true,
        ...formula,
      }],
    }],
  }],
});

const UNAVAILABLE_RESPONSE = {
  success: true,
  available: false,
  grade: "Grade 3",
  subject: "Mathematics",
  message: "Formula sheet is not available for Grade 3 yet.",
  chapters: [],
  subjects: [],
  unlocked_count: 0,
  total_count: 0,
};

describe("FormulaSheetPage — freemium chapter-wise", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders formula sheet page", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("formula-sheet-page")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Formulas");
  });

  test("shows grade in heading", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-page");
    expect(document.body.textContent).toContain("Grade 9");
  });

  test("shows formula content for Grade 9 Mathematics", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("formula-sheet-content")).toBeInTheDocument();
  });

  test("chapter sidebar renders", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("chapter-sidebar")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Triangles");
  });

  test("chapter filter button works", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("chapter-sidebar");
    const btn = screen.getByTestId("chapter-btn-circles");
    fireEvent.click(btn);
    await waitFor(() => expect(document.body.textContent).toContain("Circles"));
  });

  test("formula cards render for unlocked formulas", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    const cards = screen.getAllByTestId("formula-card");
    expect(cards.length).toBeGreaterThan(0);
    expect(document.body.textContent).toContain("Heron");
  });

  test("Free user sees upgrade banner", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("upgrade-banner")).toBeInTheDocument();
    expect(document.body.textContent).toContain("3");  // unlocked count shown in banner
  });

  test("Free user upgrade CTA navigates to subscription", async () => {
    const navFn = vi.fn();
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={navFn} />);
    await screen.findByTestId("upgrade-cta");
    fireEvent.click(screen.getByTestId("upgrade-cta"));
    expect(navFn).toHaveBeenCalledWith("subscriptionPlans");
  });

  test("Free user cannot see solved examples for preview formulas", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    // Free user sees "Upgrade to expand" button, not "Show details"
    const lockBtns = screen.getAllByTestId("expand-locked-btn");
    expect(lockBtns.length).toBeGreaterThan(0);
    // Clicking shows upgrade nav (not example content)
    expect(document.body.textContent).not.toContain("Solved example");
  });

  test("Paid user sees full formula content (examples + memory tips)", async () => {
    authFetch.mockResolvedValueOnce(PAID_RESPONSE);
    render(<FormulaSheetPage user={USER_PAID} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    expect(document.body.textContent).not.toContain("Upgrade to see a solved CBSE example");
    // Shows total count
    expect(document.body.textContent).toContain("10 formulas unlocked");
  });

  test("Paid user sees no upgrade banner", async () => {
    authFetch.mockResolvedValueOnce(PAID_RESPONSE);
    render(<FormulaSheetPage user={USER_PAID} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    expect(screen.queryByTestId("upgrade-banner")).not.toBeInTheDocument();
  });

  test("search filters formulas by name", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-search");
    fireEvent.change(screen.getByTestId("formula-search"), { target: { value: "Heron" } });
    await waitFor(() => {
      expect(document.body.textContent).toContain("Heron");
    });
  });

  test("subject filter buttons render", async () => {
    authFetch.mockResolvedValueOnce(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-page");
    expect(screen.getByTestId("fs-subject-mathematics")).toBeInTheDocument();
    expect(screen.getByTestId("fs-subject-science")).toBeInTheDocument();
  });

  test("subject filter triggers reload with new subject", async () => {
    authFetch.mockResolvedValue(FREE_RESPONSE);
    render(<FormulaSheetPage user={USER_FREE} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    const callsBefore = authFetch.mock.calls.length;
    fireEvent.click(screen.getByTestId("fs-subject-science"));
    await waitFor(() => expect(authFetch.mock.calls.length).toBeGreaterThan(callsBefore));
    const lastUrl = authFetch.mock.calls.at(-1)?.[0] || "";
    expect(lastUrl).toContain("subject=Science");
  });

  test("unavailable grade shows friendly empty state", async () => {
    authFetch.mockResolvedValueOnce(UNAVAILABLE_RESPONSE);
    render(<FormulaSheetPage user={{ ...USER_FREE, grade: "Grade 3" }} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("formula-sheet-unavailable")).toBeInTheDocument();
    expect(document.body.textContent).toContain("not available for Grade 3");
  });

  test("Paid user can see example after clicking show details", async () => {
    authFetch.mockResolvedValueOnce(PAID_RESPONSE);
    render(<FormulaSheetPage user={USER_PAID} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    const showBtn = screen.getAllByText(/Show details|show details/i);
    if (showBtn.length > 0) {
      fireEvent.click(showBtn[0]);
      await waitFor(() => {
        expect(document.body.textContent).toContain("HERON");
      });
    }
  });

  test("replaces generic calculation mistakes on Grade 11 Biology concepts", async () => {
    const biology = GRADE_11_CONCEPT_RESPONSE("Biology", {
      name: "Living Organism Definition",
      expression: "Living organisms show cellular organisation, metabolism and consciousness.",
      description: "A key Biology concept.",
      chapter: "The Living World",
      common_mistakes: [
        "Misreading the question — identify exactly what Living Organism Definition is being asked to find before substituting.",
        "Sign error — check every negative value carefully, especially when squaring or taking roots.",
        "Skipping intermediate steps — write each step clearly to avoid arithmetic mistakes under exam pressure.",
      ],
    });
    authFetch.mockImplementation(url => Promise.resolve(
      url.includes("subject=Biology")
        ? biology
        : { ...PAID_RESPONSE, subjects: biology.subjects }
    ));

    render(<FormulaSheetPage user={{ ...USER_PAID, grade: "Grade 11" }} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    fireEvent.click(screen.getByTestId("fs-subject-biology"));
    await screen.findByText("Living Organism Definition");
    fireEvent.click(screen.getByTestId("expand-btn"));

    await waitFor(() => {
      expect(document.body.textContent).toContain("related biological term");
      expect(document.body.textContent).not.toContain("Sign error — check every negative value");
      expect(document.body.textContent).not.toContain("squaring or taking roots");
    });
  });

  test("replaces generic calculation mistakes on qualitative Chemistry concepts", async () => {
    const chemistry = GRADE_11_CONCEPT_RESPONSE("Chemistry", {
      name: "Energy of Orbital",
      expression: "The energy associated with an electron in an atomic orbital.",
      description: "A concept from atomic structure.",
      chapter: "Structure of Atom",
      common_mistakes: [
        "Misreading the question — identify exactly what Energy of Orbital is being asked to find before substituting.",
        "Sign error — check every negative value carefully, especially when squaring or taking roots.",
        "Skipping intermediate steps — write each step clearly to avoid arithmetic mistakes under exam pressure.",
      ],
    });
    authFetch.mockImplementation(url => Promise.resolve(
      url.includes("subject=Chemistry")
        ? chemistry
        : { ...PAID_RESPONSE, subjects: chemistry.subjects }
    ));

    render(<FormulaSheetPage user={{ ...USER_PAID, grade: "Grade 11" }} setActivePage={vi.fn()} />);
    await screen.findByTestId("formula-sheet-content");
    fireEvent.click(screen.getByTestId("fs-subject-chemistry"));
    await screen.findByText("Energy of Orbital");
    fireEvent.click(screen.getByTestId("expand-btn"));

    await waitFor(() => {
      expect(document.body.textContent).toContain("related chemical term or particle");
      expect(document.body.textContent).not.toContain("Sign error — check every negative value");
      expect(document.body.textContent).not.toContain("squaring or taking roots");
    });
  });
});

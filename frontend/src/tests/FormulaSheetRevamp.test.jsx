/**
 * FormulaSheetRevamp.test.jsx
 * Regression tests for FormulaSheetPage revamp:
 *   - Grade selector (5-12): every account (paid or free) is locked to its
 *     enrolled grade — the backend enforces this too, so it isn't a paywall
 *   - Difficulty filter
 *   - Sort selector
 *   - Studied toggle (localStorage)
 *   - Ask AI button (navigates to doubt + sets sessionStorage)
 *   - Subject icons rendered
 *   - Existing tests: search, upgrade banner, chapter sidebar, expand still work
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import FormulaSheetPage from "../pages/FormulaSheetPage";

// ── Mock authFetch ────────────────────────────────────────────────────────────
vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));
import { authFetch } from "../api/authClient";

// ── Mock hasPaidAccess ────────────────────────────────────────────────────────
vi.mock("../utils/resolveSubscription", () => ({
  hasPaidAccess: vi.fn(),
}));
import { hasPaidAccess } from "../utils/resolveSubscription";

// ── Test data ─────────────────────────────────────────────────────────────────
const FORMULA_RESPONSE = {
  success: true,
  available: true,
  grade: "Grade 9",
  subject: "Mathematics",
  subjects: ["Mathematics", "Science", "Physics", "Chemistry"],
  has_premium: false,
  unlocked_count: 3,
  total_count: 12,
  chapters: [
    {
      chapter_id: "polynomials",
      chapter_name: "Polynomials",
      chapter_order: 1,
      total_formulas: 3,
      unlocked_count: 3,
      locked: false,
      topics: [
        {
          topic_name: "General",
          formulas: [
            {
              id: "f1",
              name: "Remainder Theorem",
              expression: "p(a) = remainder when p(x) / (x-a)",
              description: "Remainder when p(x) is divided by (x-a)",
              chapter: "Polynomials",
              difficulty: "medium",
              tags: ["polynomial"],
              locked: false,
              preview_allowed: true,
            },
            {
              id: "f2",
              name: "Factor Theorem",
              expression: "(x-a) is a factor iff p(a) = 0",
              description: "Factor of a polynomial",
              chapter: "Polynomials",
              difficulty: "easy",
              tags: [],
              locked: false,
              preview_allowed: true,
            },
            {
              id: "f3",
              name: "Hard Identity",
              expression: "(a+b+c)^2 = a^2+b^2+c^2+2ab+2bc+2ca",
              description: "Three-term expansion",
              chapter: "Polynomials",
              difficulty: "hard",
              tags: [],
              locked: false,
              preview_allowed: true,
            },
          ],
        },
      ],
    },
  ],
};

const PAID_RESPONSE = {
  ...FORMULA_RESPONSE,
  has_premium: true,
  unlocked_count: 12,
};

const FREE_USER = {
  grade: "Grade 9",
  role: "student",
  accessCbse: false,
  subscriptionPlan: "free",
};

const PAID_USER = {
  grade: "Grade 9",
  role: "student",
  accessCbse: true,
  subscriptionPlan: "premium",
  subscriptionExpiresAt: new Date(Date.now() + 86400000).toISOString(),
};

const setActivePage = vi.fn();

// ── Setup / teardown ──────────────────────────────────────────────────────────
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  authFetch.mockResolvedValue(FORMULA_RESPONSE);
  hasPaidAccess.mockReturnValue(false);
});

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// ── Helpers ───────────────────────────────────────────────────────────────────
async function renderAndLoad(user = FREE_USER, response = FORMULA_RESPONSE) {
  authFetch.mockResolvedValue(response);
  hasPaidAccess.mockReturnValue(user === PAID_USER);
  render(<FormulaSheetPage user={user} setActivePage={setActivePage} />);
  await waitFor(() => screen.findByTestId("formula-sheet-content"));
}

// ══════════════════════════════════════════════════════════════════════════════
// Grade selector
// ══════════════════════════════════════════════════════════════════════════════

describe("Grade selector", () => {
  it("renders grade buttons 5–12", async () => {
    await renderAndLoad();
    const gradeRow = screen.getByTestId("grade-selector-row");
    expect(gradeRow).toBeTruthy();
    for (const g of ["5", "6", "7", "8", "9", "10", "11", "12"]) {
      expect(screen.getByTestId(`grade-btn-grade-${g}`)).toBeTruthy();
    }
  });

  it("enrolled grade button is active for free user", async () => {
    await renderAndLoad(FREE_USER);
    const btn = screen.getByTestId("grade-btn-grade-9");
    // jsdom normalises hex to rgb — check for either
    const bg = btn.style.background;
    expect(bg.includes("6366f1") || bg.includes("99, 102, 241")).toBe(true);
  });

  it("non-enrolled grade buttons are dimmed for free user", async () => {
    await renderAndLoad(FREE_USER);
    const btn = screen.getByTestId("grade-btn-grade-10");
    expect(btn.style.opacity).toBe("0.55");
    expect(btn.style.cursor).toBe("default");
  });

  it("clicking locked grade does NOT trigger API call for free user", async () => {
    await renderAndLoad(FREE_USER);
    const btn = screen.getByTestId("grade-btn-grade-10");
    const callsBefore = authFetch.mock.calls.length;
    fireEvent.click(btn);
    // Should NOT fire a new API call
    expect(authFetch.mock.calls.length).toBe(callsBefore);
  });

  it("paid user is ALSO locked to their enrolled grade — backend enforces this for everyone", async () => {
    hasPaidAccess.mockReturnValue(true);
    authFetch.mockResolvedValue(PAID_RESPONSE);
    render(<FormulaSheetPage user={PAID_USER} setActivePage={setActivePage} />);
    await waitFor(() => screen.findByTestId("formula-sheet-content"));
    const callsBefore = authFetch.mock.calls.length;
    const btn = screen.getByTestId("grade-btn-grade-10");
    expect(btn.style.opacity).toBe("0.55"); // still dimmed/locked, same as a free user
    fireEvent.click(btn);
    expect(authFetch.mock.calls.length).toBe(callsBefore); // no new call fired
  });

  it("shows a clear grade-mismatch message on a 403, not the generic fallback", async () => {
    const gradeMismatchError = new Error("This student is onboarded for Grade 9.");
    gradeMismatchError.status = 403;
    authFetch.mockRejectedValue(gradeMismatchError);
    render(<FormulaSheetPage user={FREE_USER} setActivePage={setActivePage} />);

    expect(await screen.findByText(/you can only view formula sheets for your own grade \(grade 9\)/i))
      .toBeTruthy();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Subject icons
// ══════════════════════════════════════════════════════════════════════════════

describe("Subject tabs with icons", () => {
  it("renders subject tabs with icons from API response", async () => {
    await renderAndLoad();
    expect(screen.getByTestId("fs-subject-mathematics")).toBeTruthy();
    expect(screen.getByTestId("fs-subject-science")).toBeTruthy();
  });

  it("active subject tab is highlighted", async () => {
    await renderAndLoad();
    const mathBtn = screen.getByTestId("fs-subject-mathematics");
    // jsdom normalises hex to rgb — check for either form
    const bg = mathBtn.style.background;
    expect(bg.includes("6366f1") || bg.includes("99, 102, 241")).toBe(true);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Difficulty filter
// ══════════════════════════════════════════════════════════════════════════════

describe("Difficulty filter", () => {
  it("renders difficulty filter dropdown", async () => {
    await renderAndLoad();
    expect(screen.getByTestId("difficulty-filter")).toBeTruthy();
  });

  it("filtering by 'easy' shows only easy formulas", async () => {
    await renderAndLoad();
    // First select a chapter
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    // Then apply difficulty filter
    const filter = screen.getByTestId("difficulty-filter");
    fireEvent.change(filter, { target: { value: "easy" } });
    await waitFor(() => {
      const cards = screen.getAllByTestId("formula-card");
      // Only "Factor Theorem" has difficulty=easy
      expect(cards.length).toBe(1);
    });
  });

  it("filtering by 'hard' shows only hard formulas", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    const filter = screen.getByTestId("difficulty-filter");
    fireEvent.change(filter, { target: { value: "hard" } });
    await waitFor(() => {
      const cards = screen.getAllByTestId("formula-card");
      expect(cards.length).toBe(1);
    });
  });

  it("clearing difficulty filter shows all formulas", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    const filter = screen.getByTestId("difficulty-filter");
    fireEvent.change(filter, { target: { value: "easy" } });
    fireEvent.change(filter, { target: { value: "" } });
    await waitFor(() => {
      const cards = screen.getAllByTestId("formula-card");
      expect(cards.length).toBe(3);
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Sort selector
// ══════════════════════════════════════════════════════════════════════════════

describe("Sort selector", () => {
  it("renders sort dropdown", async () => {
    await renderAndLoad();
    expect(screen.getByTestId("sort-select")).toBeTruthy();
  });

  it("A→Z sort orders formula names alphabetically", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    const sort = screen.getByTestId("sort-select");
    fireEvent.change(sort, { target: { value: "az" } });
    await waitFor(() => {
      const cards = screen.getAllByTestId("formula-card");
      expect(cards.length).toBe(3);
      // The first card should be "Factor Theorem" (F < H < R alphabetically)
      expect(cards[0].textContent).toContain("Factor Theorem");
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Studied toggle
// ══════════════════════════════════════════════════════════════════════════════

describe("Studied toggle", () => {
  it("renders 'Mark studied' button on each preview card", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => {
      const toggles = screen.getAllByTestId("studied-toggle");
      expect(toggles.length).toBeGreaterThan(0);
      expect(toggles[0].textContent).toContain("Mark studied");
    });
  });

  it("clicking 'Mark studied' changes button text to '✓ Studied'", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("studied-toggle"));
    const toggle = screen.getAllByTestId("studied-toggle")[0];
    fireEvent.click(toggle);
    expect(toggle.textContent).toContain("Studied");
  });

  it("studied state is persisted to localStorage", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("studied-toggle"));
    const toggle = screen.getAllByTestId("studied-toggle")[0];
    fireEvent.click(toggle);
    // Check localStorage was written
    const stored = localStorage.getItem("fs_studied_Grade 9_Mathematics");
    expect(stored).toBeTruthy();
    const set = JSON.parse(stored);
    expect(set.length).toBeGreaterThan(0);
  });

  it("clicking studied again un-marks the formula", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("studied-toggle"));
    const toggle = screen.getAllByTestId("studied-toggle")[0];
    fireEvent.click(toggle); // mark
    fireEvent.click(toggle); // unmark
    expect(toggle.textContent).toContain("Mark studied");
  });

  it("studied count shown in header when formulas are studied", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("studied-toggle"));
    const toggle = screen.getAllByTestId("studied-toggle")[0];
    fireEvent.click(toggle);
    expect(screen.getByText(/1 studied/)).toBeTruthy();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Ask AI button
// ══════════════════════════════════════════════════════════════════════════════

describe("Ask AI button", () => {
  it("renders 'Ask AI' button on each preview card", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => {
      const aiButtons = screen.getAllByTestId("ask-ai-btn");
      expect(aiButtons.length).toBeGreaterThan(0);
    });
  });

  it("clicking Ask AI navigates to doubt page", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("ask-ai-btn"));
    const aiBtn = screen.getAllByTestId("ask-ai-btn")[0];
    fireEvent.click(aiBtn);
    expect(setActivePage).toHaveBeenCalledWith("doubt");
  });

  it("clicking Ask AI stores formula name in sessionStorage", async () => {
    await renderAndLoad();
    const chBtn = screen.getByTestId("chapter-btn-polynomials");
    fireEvent.click(chBtn);
    await waitFor(() => screen.getAllByTestId("ask-ai-btn"));
    const aiBtn = screen.getAllByTestId("ask-ai-btn")[0];
    fireEvent.click(aiBtn);
    const stored = sessionStorage.getItem("doubt_prefill");
    expect(stored).toBeTruthy();
    expect(stored).toContain("Remainder Theorem");
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Search still works (regression)
// ══════════════════════════════════════════════════════════════════════════════

describe("Search (regression)", () => {
  it("filters formulas by name", async () => {
    await renderAndLoad();
    const search = screen.getByTestId("formula-search");
    fireEvent.change(search, { target: { value: "Factor" } });
    await waitFor(() => {
      const cards = screen.getAllByTestId("formula-card");
      expect(cards.length).toBe(1);
      expect(cards[0].textContent).toContain("Factor Theorem");
    });
  });

  it("shows 'No formulas match' when search has no results", async () => {
    await renderAndLoad();
    const search = screen.getByTestId("formula-search");
    fireEvent.change(search, { target: { value: "xyznonexistent999" } });
    await waitFor(() => {
      expect(screen.getByText(/No formulas match/i)).toBeTruthy();
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Upgrade banner (regression — free user)
// ══════════════════════════════════════════════════════════════════════════════

describe("Upgrade banner (regression)", () => {
  it("shows upgrade banner for free user", async () => {
    await renderAndLoad(FREE_USER, FORMULA_RESPONSE);
    expect(screen.getByTestId("upgrade-banner")).toBeTruthy();
  });

  it("upgrade button calls setActivePage with subscriptionPlans", async () => {
    await renderAndLoad(FREE_USER, FORMULA_RESPONSE);
    const btn = screen.getByTestId("upgrade-cta");
    fireEvent.click(btn);
    expect(setActivePage).toHaveBeenCalledWith("subscriptionPlans");
  });

  it("no upgrade banner for paid user", async () => {
    hasPaidAccess.mockReturnValue(true);
    authFetch.mockResolvedValue(PAID_RESPONSE);
    render(<FormulaSheetPage user={PAID_USER} setActivePage={setActivePage} />);
    await waitFor(() => screen.findByTestId("formula-sheet-content"));
    expect(screen.queryByTestId("upgrade-banner")).toBeNull();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Chapter sidebar (regression)
// ══════════════════════════════════════════════════════════════════════════════

describe("Chapter sidebar (regression)", () => {
  it("renders chapter sidebar when no search active", async () => {
    await renderAndLoad();
    expect(screen.getByTestId("chapter-sidebar")).toBeTruthy();
  });

  it("hides chapter sidebar when search is active", async () => {
    await renderAndLoad();
    const search = screen.getByTestId("formula-search");
    fireEvent.change(search, { target: { value: "Factor" } });
    await waitFor(() => {
      expect(screen.queryByTestId("chapter-sidebar")).toBeNull();
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Unavailable state (regression)
// ══════════════════════════════════════════════════════════════════════════════

describe("Unavailable state (regression)", () => {
  it("shows unavailable message when available=false", async () => {
    authFetch.mockResolvedValue({
      success: true,
      available: false,
      message: "Formula sheet not available for this grade yet.",
      chapters: [],
    });
    render(<FormulaSheetPage user={FREE_USER} setActivePage={setActivePage} />);
    await waitFor(() => {
      expect(screen.getByTestId("formula-sheet-unavailable")).toBeTruthy();
    });
  });
});

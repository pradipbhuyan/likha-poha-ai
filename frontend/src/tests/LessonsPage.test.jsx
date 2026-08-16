/**
 * LessonsPage — the core student learning surface.
 *
 * This suite was previously quarantined with describe.skip: the page had been
 * refactored to render through getChapterDoc() + <ChapterJourneyView>, while
 * the tests still mocked the old generateLesson()/step-based UI and asserted
 * on a "Generated Lesson" heading that no longer exists. CI reported green
 * while covering nothing here — on the most-used student feature.
 *
 * Rewritten against the current architecture. Scope is deliberately the page's
 * own responsibilities:
 *
 *   - syllabus load, and its loading / failure states
 *   - grade and subject selectors, and the access rules that shape them
 *   - fetching the chapter doc for the current selection, and refetching when
 *     that selection changes
 *   - choosing between four render outcomes: loading, journey, exemplar
 *     paywall, and not-available
 *   - the internal-only "Refresh lesson" control
 *
 * <ChapterJourneyView> is stubbed to a props probe. Its own rendering is
 * covered by ChapterJourney.test.jsx; what matters here is that the page
 * selects it at the right time and hands it the right props.
 */
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import LessonsPage from "../pages/LessonsPage";
import { getSyllabus } from "../api/syllabus";
import { getChapterDoc } from "../api/lesson";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(),
}));

vi.mock("../api/lesson", () => ({
  getChapterDoc: vi.fn(),
}));

// Props probe. Serialises what the page passed so assertions can check the
// wiring without reaching into the real journey renderer.
vi.mock("../components/journey/ChapterJourneyView", () => ({
  default: ({ doc, grade, mode, subject, chapter }) => (
    <div
      data-testid="chapter-journey-view"
      data-grade={grade}
      data-mode={mode}
      data-subject={subject}
      data-chapter={chapter}
      data-doc-title={doc?.title || ""}
    >
      Chapter journey for {chapter}
    </div>
  ),
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const SYLLABUS = {
  "Grade 5": { CBSE: { Maths: ["Fractions"] } },
  "Grade 9": {
    CBSE: {
      Science: ["Tissues", "Motion", "Exemplar: Tissues"],
      Hindi: ["दो बैलों की कथा"],
      Maths: ["Number Systems"],
    },
  },
  "Grade 11": {
    CBSE: {
      Physics: ["Units and Measurements"],
      Accountancy: ["Theory Base of Accounting"],
    },
  },
};

const CHAPTER_DOC = { title: "Tissues", milestones: [] };

function student(overrides = {}) {
  return {
    role: "student",
    username: "test_student",
    grade: "Grade 9",
    board: "CBSE",
    accessCbse: false,
    cbseSubjects: [],
    ...overrides,
  };
}

/** Resolve when the syllabus has loaded and the selectors are on screen. */
async function renderPage(props = {}) {
  const setActivePage = vi.fn();
  const utils = render(
    <LessonsPage user={student()} setActivePage={setActivePage} {...props} />
  );
  await waitFor(() =>
    expect(screen.queryByText("Loading syllabus...")).not.toBeInTheDocument()
  );
  return { ...utils, setActivePage };
}

function selects() {
  return document.querySelectorAll("select");
}

beforeEach(() => {
  vi.clearAllMocks();
  getSyllabus.mockResolvedValue({ syllabus: SYLLABUS });
  getChapterDoc.mockResolvedValue({ success: true, available: true, doc: CHAPTER_DOC });
  vi.stubGlobal("fetch", vi.fn(async () => ({ json: async () => ({}) })));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── Syllabus load ────────────────────────────────────────────────────────────

describe("LessonsPage — syllabus load", () => {
  test("shows a loading message until the syllabus arrives", async () => {
    let release;
    getSyllabus.mockReturnValue(new Promise((resolve) => { release = resolve; }));

    render(<LessonsPage user={student()} setActivePage={vi.fn()} />);
    expect(screen.getByText("Loading syllabus...")).toBeInTheDocument();

    release({ syllabus: SYLLABUS });
    await waitFor(() =>
      expect(screen.queryByText("Loading syllabus...")).not.toBeInTheDocument()
    );
  });

  test("shows an error when the syllabus cannot be loaded", async () => {
    getSyllabus.mockRejectedValue(new Error("network down"));

    render(<LessonsPage user={student()} setActivePage={vi.fn()} />);

    expect(await screen.findByText("Could not load syllabus")).toBeInTheDocument();
    expect(getChapterDoc).not.toHaveBeenCalled();
  });

  test("defaults the selection to the student's own grade", async () => {
    await renderPage();
    const [gradeSelect] = selects();
    expect(gradeSelect.value).toBe("Grade 9");
  });
});

// ── Selector access rules ────────────────────────────────────────────────────

describe("LessonsPage — selector access rules", () => {
  test("a student sees only their onboarded grade", async () => {
    await renderPage();

    const [gradeSelect] = selects();
    const options = [...gradeSelect.options].map((o) => o.value);
    expect(options).toEqual(["Grade 9"]);
    expect(options).not.toContain("Grade 5");
  });

  test("the internal all-access test account sees every grade", async () => {
    await renderPage({ user: student({ username: "akshita.teststudent" }) });

    const [gradeSelect] = selects();
    const options = [...gradeSelect.options].map((o) => o.value);
    expect(options).toEqual(expect.arrayContaining(["Grade 5", "Grade 9", "Grade 11"]));
  });

  test("subjects are limited to the student's enrolled cbseSubjects", async () => {
    await renderPage({ user: student({ cbseSubjects: ["Science"] }) });

    const [, subjectSelect] = selects();
    const options = [...subjectSelect.options].map((o) => o.value);
    expect(options).toEqual(["Science"]);
    expect(options).not.toContain("Hindi");
  });

  test("an empty cbseSubjects list means every subject is available", async () => {
    await renderPage();

    const [, subjectSelect] = selects();
    const options = [...subjectSelect.options].map((o) => o.value);
    expect(options).toEqual(expect.arrayContaining(["Science", "Hindi", "Maths"]));
  });

  test("changing subject resets the chapter to that subject's first", async () => {
    await renderPage();
    const [, subjectSelect, chapterSelect] = selects();

    fireEvent.change(subjectSelect, { target: { value: "Maths" } });

    await waitFor(() => expect(chapterSelect.value).toBe("Number Systems"));
  });
});

// ── Chapter doc fetching ─────────────────────────────────────────────────────

describe("LessonsPage — chapter doc fetching", () => {
  test("requests the chapter doc for the resolved selection", async () => {
    await renderPage();

    await waitFor(() => expect(getChapterDoc).toHaveBeenCalled());
    expect(getChapterDoc).toHaveBeenCalledWith(
      expect.objectContaining({
        grade: "Grade 9",
        mode: "CBSE",
        board: "CBSE",
        subject: "Science",
        chapter: "Tissues",
      })
    );
  });

  test("refetches when the chapter changes", async () => {
    await renderPage();
    await waitFor(() => expect(getChapterDoc).toHaveBeenCalledTimes(1));

    const [, , chapterSelect] = selects();
    fireEvent.change(chapterSelect, { target: { value: "Motion" } });

    await waitFor(() =>
      expect(getChapterDoc).toHaveBeenLastCalledWith(
        expect.objectContaining({ chapter: "Motion" })
      )
    );
  });

  test("shows the loading animation and hides the selectors while fetching", async () => {
    let release;
    getChapterDoc.mockReturnValue(new Promise((resolve) => { release = resolve; }));

    await renderPage();

    expect(
      await screen.findByAltText("Likha Poha AI is loading your chapter…")
    ).toBeInTheDocument();
    expect(screen.getByText("Loading your chapter…")).toBeInTheDocument();
    expect(selects()).toHaveLength(0);

    release({ success: true, available: true, doc: CHAPTER_DOC });
    await waitFor(() => expect(selects()).toHaveLength(3));
  });
});

// ── Render outcomes ──────────────────────────────────────────────────────────

describe("LessonsPage — render outcomes", () => {
  test("renders the chapter journey when a doc is available", async () => {
    await renderPage();

    const view = await screen.findByTestId("chapter-journey-view");
    expect(view).toHaveAttribute("data-grade", "Grade 9");
    expect(view).toHaveAttribute("data-mode", "CBSE");
    expect(view).toHaveAttribute("data-subject", "Science");
    expect(view).toHaveAttribute("data-chapter", "Tissues");
    expect(view).toHaveAttribute("data-doc-title", "Tissues");
  });

  test("shows the not-ready state when no doc exists, naming the chapter", async () => {
    getChapterDoc.mockResolvedValue({ success: true, available: false, doc: null });

    await renderPage();

    expect(await screen.findByText("This chapter isn't available yet")).toBeInTheDocument();
    // The chapter name is echoed in the body copy, in a <strong>. Scoped to
    // that element because the name also appears as a dropdown <option>.
    expect(
      screen.getByText("Tissues", { selector: "strong" })
    ).toBeInTheDocument();
    expect(screen.queryByTestId("chapter-journey-view")).not.toBeInTheDocument();
  });

  test("treats available:false with a doc payload as unavailable", async () => {
    getChapterDoc.mockResolvedValue({ success: true, available: false, doc: CHAPTER_DOC });

    await renderPage();

    expect(await screen.findByText("This chapter isn't available yet")).toBeInTheDocument();
  });

  test("falls back to the not-ready state when the fetch fails", async () => {
    getChapterDoc.mockRejectedValue(new Error("boom"));

    await renderPage();

    expect(await screen.findByText("This chapter isn't available yet")).toBeInTheDocument();
  });
});

// ── Exemplar paywall ─────────────────────────────────────────────────────────

describe("LessonsPage — exemplar paywall", () => {
  const exemplar = "Exemplar: Tissues";

  async function selectExemplarChapter() {
    const [, , chapterSelect] = selects();
    fireEvent.change(chapterSelect, { target: { value: exemplar } });
    return chapterSelect;
  }

  test("locks an exemplar chapter for a free student", async () => {
    await renderPage();
    await selectExemplarChapter();

    expect(await screen.findByText("Upgrade to unlock this chapter")).toBeInTheDocument();
    expect(screen.getByText("🔒 Exemplar Lesson — Paid Only")).toBeInTheDocument();
    expect(screen.queryByTestId("chapter-journey-view")).not.toBeInTheDocument();
  });

  test("the upgrade button routes to the subscription page", async () => {
    const { setActivePage } = await renderPage();
    await selectExemplarChapter();

    fireEvent.click(await screen.findByRole("button", { name: /Upgrade to Unlock/i }));

    expect(setActivePage).toHaveBeenCalledWith("subscriptionPlans");
  });

  test("marks locked exemplar chapters in the dropdown for a free student", async () => {
    await renderPage();

    const [, , chapterSelect] = selects();
    const locked = [...chapterSelect.options].find((o) => o.value === exemplar);
    expect(locked.textContent).toBe(`🔒 ${exemplar}`);

    const open = [...chapterSelect.options].find((o) => o.value === "Tissues");
    expect(open.textContent).toBe("Tissues");
  });

  test("a student with accessCbse can open an exemplar chapter", async () => {
    await renderPage({ user: student({ accessCbse: true }) });
    await selectExemplarChapter();

    expect(await screen.findByTestId("chapter-journey-view")).toBeInTheDocument();
    expect(screen.queryByText("Upgrade to unlock this chapter")).not.toBeInTheDocument();
  });

  test("an unexpired subscription also unlocks exemplar chapters", async () => {
    const future = new Date(Date.now() + 7 * 86400_000).toISOString();
    await renderPage({ user: student({ subscriptionExpiresAt: future }) });
    await selectExemplarChapter();

    expect(await screen.findByTestId("chapter-journey-view")).toBeInTheDocument();
  });

  test("an expired subscription does not unlock exemplar chapters", async () => {
    const past = new Date(Date.now() - 86400_000).toISOString();
    await renderPage({ user: student({ subscriptionExpiresAt: past }) });
    await selectExemplarChapter();

    expect(await screen.findByText("Upgrade to unlock this chapter")).toBeInTheDocument();
  });

  test("parentId alone does not unlock exemplar chapters", async () => {
    // Regression: a free-plan parent's child has parentId but no paid access.
    await renderPage({ user: student({ parentId: "parent-123" }) });
    await selectExemplarChapter();

    expect(await screen.findByText("Upgrade to unlock this chapter")).toBeInTheDocument();
  });
});

// ── Refresh lesson (internal QA tool) ────────────────────────────────────────

describe("LessonsPage — refresh lesson control", () => {
  const REFRESH = /Refresh lesson/i;

  test("is hidden from an ordinary student", async () => {
    await renderPage();

    await screen.findByTestId("chapter-journey-view");
    expect(screen.queryByRole("button", { name: REFRESH })).not.toBeInTheDocument();
  });

  test("is shown to the internal all-access test account", async () => {
    await renderPage({ user: student({ username: "akshita.teststudent" }) });

    expect(await screen.findByRole("button", { name: REFRESH })).toBeInTheDocument();
  });

  test("refetches with refresh:true to bypass the server-side cache", async () => {
    await renderPage({ user: student({ username: "akshita.teststudent" }) });

    fireEvent.click(await screen.findByRole("button", { name: REFRESH }));

    await waitFor(() =>
      expect(getChapterDoc).toHaveBeenLastCalledWith(
        expect.objectContaining({ refresh: true })
      )
    );
  });

  test("keeps the current lesson on screen when a refresh fails", async () => {
    await renderPage({ user: student({ username: "akshita.teststudent" }) });
    await screen.findByTestId("chapter-journey-view");

    getChapterDoc.mockRejectedValueOnce(new Error("refresh failed"));
    fireEvent.click(screen.getByRole("button", { name: REFRESH }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: REFRESH })).toBeEnabled()
    );
    // A failed refresh must not blank out a lesson that was already correct.
    expect(screen.getByTestId("chapter-journey-view")).toBeInTheDocument();
  });
});

// ── Grade 11/12 profile sync ─────────────────────────────────────────────────

describe("LessonsPage — Grade 11/12 profile sync", () => {
  test("fetches the profile when stream and subjects are missing", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      json: async () => ({ stream: "Science", cbse_subjects: ["Physics"], grade: "Grade 11" }),
    })));

    await renderPage({
      user: student({ grade: "Grade 11", accessToken: "token-123", cbseSubjects: [] }),
    });

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain("/api/auth/profile");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });

  test("does not fetch when the stream is already known", async () => {
    await renderPage({
      user: student({
        grade: "Grade 11",
        accessToken: "token-123",
        stream: "Science",
        cbseSubjects: ["Physics"],
      }),
    });

    expect(fetch).not.toHaveBeenCalled();
  });

  test("does not fetch for a lower grade", async () => {
    await renderPage({ user: student({ grade: "Grade 9", accessToken: "token-123" }) });

    expect(fetch).not.toHaveBeenCalled();
  });

  test("renders normally when the profile sync fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));

    await renderPage({
      user: student({ grade: "Grade 11", accessToken: "token-123", cbseSubjects: [] }),
    });

    expect(await screen.findByTestId("chapter-journey-view")).toBeInTheDocument();
  });
});

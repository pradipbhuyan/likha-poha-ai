import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import Sidebar from "../components/Sidebar";

function renderSidebar(user, activePage = "dashboard", { mobileNavOpen = false } = {}) {
  /** Render the shared sidebar with minimal shell callbacks. */
  const setActivePage = vi.fn();
  const setMobileNavOpen = vi.fn();

  const view = render(
    <Sidebar
      activePage={activePage}
      setActivePage={setActivePage}
      user={user}
      onLogout={vi.fn()}
      mobileNavOpen={mobileNavOpen}
      setMobileNavOpen={setMobileNavOpen}
    />
  );

  return { setActivePage, setMobileNavOpen, ...view };
}

const STUDENT_GROUP_ORDER = [
  "Home",
  "Learn",
  "Practise & Prepare",
  "Revision Tools",
  "Progress",
  "Help & Account",
];

const STUDENT_PAGE_ORDER = [
  "Dashboard",
  "Lessons",
  "Ask Doubt",
  "Mock Test",
  "Exam Prep Center",
  "Board Papers",
  "Formulas & Concepts",
  "Exemplar Research",
  "Learn More",
  "Analytics",
  "Leaderboard",
  "Platform Walkthrough",
  "Subscription",
  "Change Password",
];

describe("Sidebar role visibility", () => {
  test("hides student, parent, and teacher pages from admin navigation", () => {
    renderSidebar({
      role: "admin",
      username: "Pradip Admin",
    });

    expect(screen.getByRole("button", { name: /admin control/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rag upload/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /syllabus review/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pricing calculator/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /likha poha ai guide/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sales incentives/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sales collaterals/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /teacher dashboard/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /lessons/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /parent dashboard/i })).not.toBeInTheDocument();
  });

  test("shows teacher dashboard only for teacher users", () => {
    const { setActivePage } = renderSidebar(
      {
        role: "teacher",
        username: "Science Teacher",
      },
      "teacherDashboard"
    );

    expect(screen.getByRole("button", { name: /teacher dashboard/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /admin control/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /subscription/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /teacher dashboard/i }));
    expect(setActivePage).toHaveBeenCalledWith("teacherDashboard");
  });

  test("shows sales workspace pages for sales users", () => {
    const { setActivePage } = renderSidebar(
      {
        role: "sales",
        username: "Sales Partner",
      },
      "salesLeads"
    );

    // Sales users see the new lead claims dashboard (not the admin-only Sales Incentives)
    expect(screen.getByRole("button", { name: /my lead claims/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /product demo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sales collaterals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /change password/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /sales incentives/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /admin control/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /teacher dashboard/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /sales collaterals/i }));
    expect(setActivePage).toHaveBeenCalledWith("salesCollaterals");
  });
});

describe("Sidebar information architecture (student)", () => {
  const student = {
    role: "student",
    username: "Aisha",
    grade: "Grade 11", // satisfies Exam Prep, Board Papers, and Exemplar grade filters
  };

  test("renders every student route in the expected group order", () => {
    renderSidebar(student);

    const nav = screen.getByRole("navigation", { name: /main navigation/i });
    const buttonLabels = within(nav)
      .getAllByRole("button")
      .map((btn) => btn.textContent.trim());

    expect(buttonLabels).toEqual(STUDENT_PAGE_ORDER);
  });

  test("renders group labels in the expected section order", () => {
    renderSidebar(student);

    const nav = screen.getByRole("navigation", { name: /main navigation/i });
    const groupLabels = within(nav)
      .getAllByText((_, el) => el?.tagName === "P" && el.classList.contains("sidebar-group-label"))
      .map((el) => el.textContent);

    expect(groupLabels).toEqual(STUDENT_GROUP_ORDER);
  });

  test("group labels are subtle, non-interactive text — not buttons or links", () => {
    renderSidebar(student);

    const learnLabel = screen.getByText("Learn", { exact: true });
    expect(learnLabel.tagName).toBe("P");
    expect(learnLabel.closest("button")).toBeNull();
    expect(learnLabel.closest("a")).toBeNull();
  });

  test("marks the active route with aria-current=page and no others", () => {
    renderSidebar(student, "mockTest");

    const active = screen.getByRole("button", { name: /mock test/i });
    expect(active).toHaveAttribute("aria-current", "page");

    const dashboard = screen.getByRole("button", { name: /dashboard/i });
    expect(dashboard).not.toHaveAttribute("aria-current");
  });

  test("does not group navigation for teacher, sales, or parent roles", () => {
    for (const role of ["teacher", "sales", "parent"]) {
      const { unmount } = renderSidebar({ role, username: `Test ${role}` });
      expect(screen.queryByText("Help & Account", { exact: true })).not.toBeInTheDocument();
      unmount();
    }
  });

  test("groups navigation for admin, using admin-specific sections", () => {
    renderSidebar({ role: "admin", username: "Pradip Admin" });

    // Admin's own sections (added alongside the sidebar consolidation).
    expect(screen.getByText("Overview", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("Content Pipeline", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("Quality & Testing", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("Sales", { exact: true })).toBeInTheDocument();

    // "Learn" only groups pages that are hidden for admin (Lessons, Ask Doubt),
    // so it should never render, even though groups are now on for this role.
    expect(screen.queryByText("Learn", { exact: true })).not.toBeInTheDocument();
  });

  test("long usernames render without breaking the sidebar layout", () => {
    const longUsername = "a".repeat(80);
    renderSidebar({ ...student, username: longUsername });

    expect(screen.getByText(longUsername)).toBeInTheDocument();
  });

  test("logout stays reachable and pinned in its own footer section", () => {
    const onLogout = vi.fn();
    render(
      <Sidebar
        activePage="dashboard"
        setActivePage={vi.fn()}
        user={student}
        onLogout={onLogout}
        mobileNavOpen={false}
        setMobileNavOpen={vi.fn()}
      />
    );

    const logoutBtn = screen.getByRole("button", { name: /logout/i });
    expect(logoutBtn.closest(".sidebar-footer")).not.toBeNull();
    fireEvent.click(logoutBtn);
    expect(onLogout).toHaveBeenCalled();
  });
});

describe("Sidebar mobile drawer", () => {
  const student = { role: "student", username: "Aisha", grade: "Grade 11" };

  test("selecting a route closes the mobile drawer", () => {
    const { setActivePage, setMobileNavOpen } = renderSidebar(student, "dashboard", {
      mobileNavOpen: true,
    });

    fireEvent.click(screen.getByRole("button", { name: /lessons/i }));

    expect(setActivePage).toHaveBeenCalledWith("lessons");
    expect(setMobileNavOpen).toHaveBeenCalledWith(false);
  });

  test("clicking the backdrop closes the drawer", () => {
    const { container, setMobileNavOpen } = renderSidebar(student, "dashboard", {
      mobileNavOpen: true,
    });

    const backdrop = container.querySelector(".mobile-nav-backdrop");
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop);

    expect(setMobileNavOpen).toHaveBeenCalledWith(false);
  });

  test("pressing Escape closes the drawer and locks/unlocks page scroll", () => {
    const { setMobileNavOpen, unmount } = renderSidebar(student, "dashboard", {
      mobileNavOpen: true,
    });

    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(setMobileNavOpen).toHaveBeenCalledWith(false);

    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  test("no backdrop is rendered when the drawer is closed", () => {
    const { container } = renderSidebar(student, "dashboard", { mobileNavOpen: false });

    expect(container.querySelector(".mobile-nav-backdrop")).toBeNull();
  });

  test("mobile close button closes the drawer", () => {
    const { setMobileNavOpen } = renderSidebar(student, "dashboard", { mobileNavOpen: true });

    fireEvent.click(screen.getByRole("button", { name: /close navigation menu/i }));
    expect(setMobileNavOpen).toHaveBeenCalledWith(false);
  });
});

describe("Sidebar avatar picker (icons, not emoji)", () => {
  const student = { role: "student", username: "Aisha", grade: "Grade 11", accessToken: "tok" };

  test("opening the picker renders 10 preset-avatar icon buttons with no emoji text", () => {
    renderSidebar(student);

    fireEvent.click(screen.getByTitle(/click to change avatar/i));

    expect(screen.getByText("Choose Avatar")).toBeInTheDocument();
    // Every preset avatar renders an <svg> icon, not an emoji character.
    const presetButtons = screen.getAllByRole("button").filter(
      (btn) => btn.querySelector("svg") && btn.style.borderRadius === "50%" && btn.style.width === "40px"
    );
    expect(presetButtons).toHaveLength(10);
    presetButtons.forEach((btn) => {
      expect(btn.textContent.trim()).toBe("");
    });
  });

  test("Upload, Camera, and Remove Avatar controls render an icon alongside their label", () => {
    renderSidebar(student);
    fireEvent.click(screen.getByTitle(/click to change avatar/i));

    const uploadLabel = screen.getByText("Upload").closest("label");
    expect(uploadLabel.querySelector("svg")).not.toBeNull();

    const removeBtn = screen.getByText(/remove avatar/i).closest("button");
    expect(removeBtn.querySelector("svg")).not.toBeNull();
  });

  test("a previously-saved preset avatar key (e.g. from before the emoji-to-icon change) still resolves to an icon, not the fallback initial", () => {
    // Regression: PRESET_AVATARS keys (boy1/girl2/etc.) were kept stable when
    // emoji were swapped for Lucide icons, so avatars saved before that
    // change keep rendering a picture instead of silently falling back.
    renderSidebar({ ...student, avatar: "girl2" });

    const avatarBubble = screen.getByTitle(/click to change avatar/i);
    expect(avatarBubble.querySelector("svg")).not.toBeNull();
    expect(avatarBubble.textContent.trim()).not.toBe("A"); // not the initial fallback
  });

  test("selecting a preset avatar saves it and closes the picker", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    globalThis.fetch = fetchMock;

    renderSidebar(student);
    fireEvent.click(screen.getByTitle(/click to change avatar/i));

    const presetButtons = screen.getAllByRole("button").filter(
      (btn) => btn.querySelector("svg") && btn.style.borderRadius === "50%" && btn.style.width === "40px"
    );
    fireEvent.click(presetButtons[0]);

    expect(screen.queryByText("Choose Avatar")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/profile/update-avatar"),
      expect.objectContaining({ method: "POST" })
    );
  });
});

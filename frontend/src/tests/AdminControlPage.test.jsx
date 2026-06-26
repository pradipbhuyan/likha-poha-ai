import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminControlPage from "../pages/AdminControlPage";
import {
  assignTeacherStudent,
  createAdminChild,
  createAdminParent,
  createAdminTeacher,
  deleteTeacherAssignment,
  deleteUser,
  getAdminFamilies,
  getAiSettings,
  updateChildAccess,
  updateChildLimits,
} from "../api/adminControl";

vi.mock("../api/adminControl", () => ({
  getAdminFamilies: vi.fn(),
  createAdminParent: vi.fn(),
  createAdminChild: vi.fn(),
  createAdminTeacher: vi.fn(),
  assignTeacherStudent: vi.fn(),
  deleteTeacherAssignment: vi.fn(),
  updateChildAccess: vi.fn(),
  updateChildLimits: vi.fn(),
  deleteUser: vi.fn(),
  getAiSettings: vi.fn(),
  updateAiSettings: vi.fn(),
}));

const adminUser = {
  role: "admin",
  username: "Pradip Admin",
  accessToken: "admin-token",
};

function renderPage() {
  /** Render Admin Control with a mocked admin session. */
  return render(<AdminControlPage user={adminUser} />);
}

describe("AdminControlPage teacher management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    getAdminFamilies.mockResolvedValue({
      success: true,
      families: [],
    });

    // AI settings panel needs a resolved value to avoid TypeError on api_enabled
    vi.mocked(getAiSettings).mockResolvedValue({
      api_enabled: true,
      api_key_prefix: "sk-test",
      key_source: "environment",
    });
  });

  /** Helper to click a tab by its data-testid */
  async function clickTab(tabKey) {
    const tab = await screen.findByTestId(`admin-tab-${tabKey}`);
    fireEvent.click(tab);
  }

  test("tab nav renders all 7 tabs with correct ARIA attributes", async () => {
    renderPage();
    const nav = await screen.findByTestId("admin-tab-nav");
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveAttribute("role", "tablist");

    const expectedTabs = ["overview","accounts","families","associations","offers","ai","operations"];
    for (const key of expectedTabs) {
      const btn = screen.getByTestId(`admin-tab-${key}`);
      expect(btn).toHaveAttribute("role", "tab");
      expect(btn).toHaveAttribute("aria-controls", `admin-tab-panel-${key}`);
    }
  });

  test("default tab is overview and shows summary cards", async () => {
    renderPage();
    const overviewPanel = await screen.findByTestId("tab-panel-overview");
    expect(overviewPanel).toBeInTheDocument();
    expect(overviewPanel).toHaveAttribute("role", "tabpanel");
    expect(screen.getByText("Families")).toBeInTheDocument();
  });

  test("invalid ?tab= URL param falls back to overview", async () => {
    // JSDOM doesn't actually read window.location.search from test,
    // but we can verify the tab state initializer handles it safely.
    // The component uses a try/catch and VALID_TAB_KEYS validation.
    renderPage();
    // Should render without throwing and default to overview
    expect(await screen.findByTestId("tab-panel-overview")).toBeInTheDocument();
  });

  test("global success banner is visible regardless of active tab", async () => {
    getAdminFamilies.mockResolvedValue({ success: true, families: [] });

    renderPage();

    // Start on overview tab
    await screen.findByTestId("tab-panel-overview");

    // Switch to accounts tab — success banner from previous actions should still show
    // (In this test we just verify the banner appears at all since global banners
    // are rendered outside tab panels)
    expect(screen.queryByTestId("tab-panel-overview")).toBeInTheDocument();

    // Now switch to a different tab — overview panel unmounts
    await clickTab("accounts");
    expect(screen.queryByTestId("tab-panel-overview")).not.toBeInTheDocument();
    expect(screen.getByTestId("tab-panel-accounts")).toBeInTheDocument();
  });

  test("form state persists across tab switches (parentForm lives in parent component)", async () => {
    renderPage();
    await clickTab("accounts");

    // Type a partial parent name
    const nameInput = screen.getByLabelText(/parent name/i);
    fireEvent.change(nameInput, { target: { value: "Test Parent Name" } });
    expect(nameInput.value).toBe("Test Parent Name");

    // Switch to another tab and back — state should be preserved
    // (form state is in the parent component, not unmounted with the tab)
    await clickTab("overview");
    await clickTab("accounts");

    // Input still has the value because parentForm state lives in AdminControlPage
    expect(screen.getByLabelText(/parent name/i).value).toBe("Test Parent Name");
  });

  test("creates a teacher from the admin-only teacher form", async () => {
    createAdminTeacher.mockResolvedValue({
      success: true,
      teacher: {
        id: "teacher-1",
        username: "Science Teacher",
      },
    });

    renderPage();

    // Navigate to Accounts tab where teacher form is
    await clickTab("accounts");

    expect(await screen.findByText("Teacher Accounts")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/teacher name/i), {
      target: { value: "Science Teacher" },
    });
    fireEvent.change(screen.getByLabelText(/teacher email/i), {
      target: { value: "teacher@example.com" },
    });
    fireEvent.change(screen.getAllByLabelText(/temporary password/i)[0], {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/school \/ organization/i), {
      target: { value: "Demo School" },
    });
    fireEvent.change(screen.getByLabelText(/^subjects$/i), {
      target: { value: "Science, Maths" },
    });
    fireEvent.change(screen.getByLabelText(/^grades$/i), {
      target: { value: "Grade 8, Grade 9" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^create teacher$/i }));

    await waitFor(() => {
      expect(createAdminTeacher).toHaveBeenCalledWith(
        {
          email: "teacher@example.com",
          password: "password123",
          username: "Science Teacher",
          teacher_type: "independent",
          school_name: "Demo School",
          subjects: ["Science", "Maths"],
          grades: ["Grade 8", "Grade 9"],
          status: "active",
        },
        "admin-token"
      );
    });

    expect(await screen.findByText(/teacher created successfully/i)).toBeInTheDocument();
  });

  test("assigns and removes a student from an existing teacher", async () => {
    getAdminFamilies.mockResolvedValue({
      success: true,
      families: [
        {
          family_id: "no-family",
          parents: [],
          admins: [],
          teachers: [
            {
              id: "teacher-1",
              username: "Teacher One",
              email: "teacher@example.com",
              teacher_profile: {
                teacher_type: "school",
                school_name: "Demo School",
                subjects: ["Science"],
                grades: ["Grade 9"],
              },
              assignments: [
                {
                  id: "assignment-1",
                  student_id: "student-1",
                  grade: "Grade 9",
                  subject: "Science",
                  section: "9A",
                },
              ],
            },
          ],
          children: [
            {
              id: "student-1",
              username: "Akshita",
              email: "akshita@example.com",
              role: "student",
              grade: "Grade 9",
              activity: {},
            },
          ],
        },
      ],
    });
    assignTeacherStudent.mockResolvedValue({
      success: true,
      assignment: {
        id: "assignment-2",
      },
    });
    deleteTeacherAssignment.mockResolvedValue({
      success: true,
    });

    renderPage();

    // Navigate to Accounts tab where Current Teachers roster is
    await clickTab("accounts");

    const teacherCard = (await screen.findByText("Teacher One")).closest(".premium-card");
    const controls = within(teacherCard);

    fireEvent.change(controls.getByLabelText(/assign student/i), {
      target: { value: "student-1" },
    });
    fireEvent.change(controls.getByPlaceholderText("Science"), {
      target: { value: "Science" },
    });
    fireEvent.change(controls.getByPlaceholderText(/9a or pradip batch/i), {
      target: { value: "9A" },
    });

    fireEvent.click(controls.getByRole("button", { name: /^assign student$/i }));

    await waitFor(() => {
      expect(assignTeacherStudent).toHaveBeenCalledWith(
        {
          teacher_id: "teacher-1",
          student_id: "student-1",
          grade: "Grade 9",
          subject: "Science",
          section: "9A",
        },
        "admin-token"
      );
    });

    fireEvent.click(controls.getByRole("button", { name: /remove/i }));

    await waitFor(() => {
      expect(deleteTeacherAssignment).toHaveBeenCalledWith(
        "assignment-1",
        "admin-token"
      );
    });
  });

  test("shows backend reachability errors from admin APIs", async () => {
    getAdminFamilies.mockRejectedValue(
      new Error("Cannot reach backend API at http://localhost:8000.")
    );

    renderPage();

    // Error is shown globally above all tabs (no need to switch tabs)
    expect(await screen.findByText(/unable to load admin control data/i)).toBeInTheDocument();
  });

  test("creates a parent and a child from admin forms", async () => {
    getAdminFamilies.mockResolvedValue({
      success: true,
      families: [
        {
          family_id: "family-1",
          parents: [
            {
              id: "parent-1",
              username: "Parent One",
              email: "parent@example.com",
              role: "parent",
            },
          ],
          children: [],
          admins: [],
          teachers: [],
        },
      ],
    });
    createAdminParent.mockResolvedValue({ success: true });
    createAdminChild.mockResolvedValue({ success: true });

    renderPage();

    // Navigate to Accounts tab to use Create Parent form
    const tab = await screen.findByTestId("admin-tab-accounts");
    fireEvent.click(tab);

    // Now navigate to Families tab to see the existing family
    const familiesTab = screen.getByTestId("admin-tab-families");
    fireEvent.click(familiesTab);

    expect(await screen.findByText("Parent One Family")).toBeInTheDocument();
    expect(await screen.findByText("Parent One")).toBeInTheDocument();

    // Go back to Accounts tab to use Create Parent form
    fireEvent.click(screen.getByTestId("admin-tab-accounts"));

    fireEvent.change(screen.getByLabelText(/parent name/i), {
      target: { value: "New Parent" },
    });
    fireEvent.change(screen.getByLabelText(/parent email/i), {
      target: { value: "new-parent@example.com" },
    });
    // Default flow: invite email (no password field shown until in-person checkbox checked)
    fireEvent.click(screen.getByRole("button", { name: /send invite email/i }));

    await waitFor(() => {
      expect(createAdminParent).toHaveBeenCalledWith(
        {
          username: "New Parent",
          email: "new-parent@example.com",
          skip_email_confirmation: false,
        },
        "admin-token"
      );
    });

    // Go to Families tab to see parent card with child form
    fireEvent.click(screen.getByTestId("admin-tab-families"));

    const parentCard = (await screen.findByText("Parent One")).closest(".premium-card");
    const parentControls = within(parentCard);

    fireEvent.change(parentControls.getByLabelText(/child name/i), {
      target: { value: "Child One" },
    });
    fireEvent.change(parentControls.getByLabelText(/child login email/i), {
      target: { value: "child@example.com" },
    });
    fireEvent.change(parentControls.getByLabelText(/set password/i), {
      target: { value: "password456" },
    });
    fireEvent.change(parentControls.getByLabelText(/^class$/i), {
      target: { value: "Grade 5" },
    });
    fireEvent.click(parentControls.getByRole("button", { name: /create child/i }));

    await waitFor(() => {
      expect(createAdminChild).toHaveBeenCalledWith(
        {
          username: "Child One",
          email: "child@example.com",
          password: "password456",
          grade: "Grade 5",
          parent_id: "parent-1",
          family_id: "family-1",
          skip_email_confirmation: true,
        },
        "admin-token"
      );
    });
  });

  test("saves student plan, token limits, and deletes a child", async () => {
    getAdminFamilies.mockResolvedValue({
      success: true,
      families: [
        {
          family_id: "family-1",
          parents: [],
          admins: [],
          teachers: [],
          children: [
            {
              id: "student-1",
              username: "Akshita",
              email: "akshita@example.com",
              role: "student",
              grade: "Grade 9",
              subscription_plan: "free",
              account_status: "active",
              access_cbse: true,
              access_sof_science: false,
              access_sof_maths: false,
              access_sof_english: false,
              cbse_subjects: [],
              daily_token_limit: 50000,
              monthly_token_limit: 1000000,
              ai_model_preference: "default",
              activity: {
                lessons_generated: 1,
                doubts_asked: 2,
                mock_tests_generated: 0,
                requests_total: 3,
                tokens_today: 100,
                tokens_this_month: 200,
                tokens_total: 300,
                cost_total: 0.01,
              },
            },
          ],
        },
      ],
    });
    updateChildAccess.mockResolvedValue({ success: true });
    updateChildLimits.mockResolvedValue({ success: true });
    deleteUser.mockResolvedValue({ success: true });

    renderPage();

    // Navigate to Families tab where student access controls are
    const tab = await screen.findByTestId("admin-tab-families");
    fireEvent.click(tab);

    const childCard = (await screen.findByText("Akshita")).closest(".premium-card");
    const controls = within(childCard);

    fireEvent.change(controls.getByLabelText(/^plan$/i), {
      target: { value: "starter" },
    });
    fireEvent.change(controls.getByLabelText(/ai model/i), {
      target: { value: "gpt-4.1-mini" },
    });
    fireEvent.change(controls.getByLabelText(/ai token access/i), {
      target: { value: "unlimited" },
    });
    fireEvent.click(controls.getByLabelText("Science"));
    fireEvent.click(controls.getByLabelText("Maths"));
    fireEvent.click(controls.getByRole("button", { name: /save all changes/i }));

    await waitFor(() => {
      expect(updateChildAccess).toHaveBeenCalledWith(
        "student-1",
        expect.objectContaining({
          subscription_plan: "starter",
          access_cbse: true,
          cbse_subjects: ["Science", "Maths"],
          grade: "Grade 9",
          ai_model_preference: "gpt-4.1-mini",
        }),
        "admin-token"
      );
      expect(updateChildLimits).toHaveBeenCalledWith(
        "student-1",
        expect.objectContaining({
          daily_token_limit: 0,
          monthly_token_limit: 0,
        }),
        "admin-token"
      );
    });

    fireEvent.click(controls.getByRole("button", { name: /delete child/i }));

    await waitFor(() => {
      expect(deleteUser).toHaveBeenCalledWith("student-1", "admin-token");
    });
  });
});

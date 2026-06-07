import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import Sidebar from "../components/Sidebar";

function renderSidebar(user, activePage = "dashboard") {
  /** Render the shared sidebar with minimal shell callbacks. */
  const setActivePage = vi.fn();

  render(
    <Sidebar
      activePage={activePage}
      setActivePage={setActivePage}
      user={user}
      onLogout={vi.fn()}
      mobileNavOpen={false}
      setMobileNavOpen={vi.fn()}
    />
  );

  return { setActivePage };
}

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
    expect(screen.queryByRole("button", { name: /subscription/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /teacher dashboard/i }));
    expect(setActivePage).toHaveBeenCalledWith("teacherDashboard");
  });

  test("shows sales workspace pages for sales users", () => {
    const { setActivePage } = renderSidebar(
      {
        role: "sales",
        username: "Sales Partner",
      },
      "salesIncentives"
    );

    expect(screen.getByRole("button", { name: /sales incentives/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /product demo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sales collaterals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /change password/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /admin control/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /teacher dashboard/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /sales collaterals/i }));
    expect(setActivePage).toHaveBeenCalledWith("salesCollaterals");
  });
});

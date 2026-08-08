/**
 * ParentSiblingComparison.test.jsx
 * Regression tests for the sibling comparison view — renders from data
 * already present in the dashboard summary payload, no new fetch.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import ParentSiblingComparison from "../components/parent/ParentSiblingComparison";

const FREE_CHILD = {
  id: "child-1", name: "Aarav", grade: "Grade 10",
  plan: { has_full_access: false, plan_name: "Free Tier" },
  mock_test_summary: { count: 3, average_score: 55 },
  activity_summary: { last_active: "2026-08-06T10:00:00Z" },
  recommendations: [{ type: "upgrade", title: "Unlock full access" }],
};

const PAID_CHILD = {
  id: "child-2", name: "Riya", grade: "Grade 8",
  plan: { has_full_access: true, plan_name: "Premium" },
  mock_test_summary: { count: 8, average_score: 82 },
  activity_summary: { last_active: "2026-08-08T09:00:00Z" },
  recommendations: [],
};

const NO_DATA_CHILD = {
  id: "child-3", name: "Kabir", grade: "Grade 6",
  plan: { has_full_access: false, plan_name: "Free Tier" },
  mock_test_summary: { count: 0, average_score: null },
  activity_summary: {},
  recommendations: [],
};

describe("ParentSiblingComparison", () => {
  test("returns null when fewer than 2 children", () => {
    const { container } = render(<ParentSiblingComparison children={[FREE_CHILD]} onOpenChild={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  test("returns null when children is empty or missing", () => {
    const { container: c1 } = render(<ParentSiblingComparison children={[]} onOpenChild={vi.fn()} />);
    expect(c1.firstChild).toBeNull();
    const { container: c2 } = render(<ParentSiblingComparison onOpenChild={vi.fn()} />);
    expect(c2.firstChild).toBeNull();
  });

  test("renders both children's names and grades", () => {
    render(<ParentSiblingComparison children={[FREE_CHILD, PAID_CHILD]} onOpenChild={vi.fn()} />);
    const table = screen.getByTestId("parent-sibling-comparison");
    expect(table.textContent).toContain("Aarav");
    expect(table.textContent).toContain("Grade 10");
    expect(table.textContent).toContain("Riya");
    expect(table.textContent).toContain("Grade 8");
  });

  test("renders mock test counts and average scores for both children", () => {
    render(<ParentSiblingComparison children={[FREE_CHILD, PAID_CHILD]} onOpenChild={vi.fn()} />);
    const table = screen.getByTestId("parent-sibling-comparison");
    expect(table.textContent).toContain("55%");
    expect(table.textContent).toContain("82%");
  });

  test("shows mixed plan status correctly for a free + paid pair", () => {
    render(<ParentSiblingComparison children={[FREE_CHILD, PAID_CHILD]} onOpenChild={vi.fn()} />);
    const table = screen.getByTestId("parent-sibling-comparison");
    expect(table.textContent).toContain("Free Tier");
    expect(table.textContent).toContain("Premium");
  });

  test("clicking a child's header calls onOpenChild with that child", () => {
    const onOpenChild = vi.fn();
    render(<ParentSiblingComparison children={[FREE_CHILD, PAID_CHILD]} onOpenChild={onOpenChild} />);
    fireEvent.click(screen.getByTestId("sibling-open-child-2"));
    expect(onOpenChild).toHaveBeenCalledWith(PAID_CHILD);
  });

  test("handles a child with zero mock tests / null average score without crashing", () => {
    render(<ParentSiblingComparison children={[FREE_CHILD, NO_DATA_CHILD]} onOpenChild={vi.fn()} />);
    const table = screen.getByTestId("parent-sibling-comparison");
    expect(table.textContent).toContain("Kabir");
    expect(table.textContent).toContain("—"); // no-data score placeholder
    expect(table.textContent).toContain("Never"); // no last_active
  });

  test("shows 'All clear' for a child with no open recommendations", () => {
    render(<ParentSiblingComparison children={[FREE_CHILD, PAID_CHILD]} onOpenChild={vi.fn()} />);
    const table = screen.getByTestId("parent-sibling-comparison");
    expect(table.textContent).toContain("All clear");
  });
});

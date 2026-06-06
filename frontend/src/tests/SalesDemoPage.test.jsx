import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SalesDemoPage from "../pages/SalesDemoPage";

describe("SalesDemoPage", () => {
  test("shows safe demo flows for student, parent, and teacher prospects", () => {
    render(
      <SalesDemoPage
        user={{
          role: "sales",
          username: "Sales Partner",
        }}
      />
    );

    expect(screen.getByText("Prospect-ready product walkthrough")).toBeInTheDocument();
    expect(screen.getByText("Sales Partner")).toBeInTheDocument();
    expect(screen.getByText("A guided study desk for every learner")).toBeInTheDocument();
    expect(screen.getAllByText("Student sign-in").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /lessons/i }));
    expect(screen.getAllByText("Step-wise AI lessons").length).toBeGreaterThan(0);
    expect(screen.getByText("Step 3: Guided Example")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /parent/i }));
    expect(screen.getByText("Clear visibility without classroom noise")).toBeInTheDocument();
    expect(screen.getAllByText("Parent sign-in").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /dashboard/i }));
    expect(screen.getAllByText("Family learning center").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /teacher/i }));
    expect(screen.getByText("A classroom view for schools and tutors")).toBeInTheDocument();
    expect(screen.getAllByText("Teacher sign-in").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /analytics/i }));
    expect(screen.getAllByText("Class analytics").length).toBeGreaterThan(0);
  });
});

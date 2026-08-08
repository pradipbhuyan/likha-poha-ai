/**
 * ProgressReportPdf.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Two layers, per the "true PDF export" plan:
 * 1. Generator-level: call generateProgressReportPdf(report) directly against
 *    a mocked jsPDF/jspdf-autotable, assert on the calls made (content shape),
 *    not on actual PDF bytes (jsdom can't meaningfully validate those).
 * 2. Component-level: render the real workspace + real generator (still against
 *    the mocked jsPDF lib) through the Report tab's Download PDF button, to
 *    verify the end-to-end wiring from click to jsPDF calls.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

var jspdfInstances = [];

vi.mock("jspdf", () => {
  function FakeJsPDF(){
    this.text = vi.fn();
    this.setFont = vi.fn();
    this.setFontSize = vi.fn();
    this.setTextColor = vi.fn();
    this.addPage = vi.fn();
    this.save = vi.fn();
    this.addImage = vi.fn();
    this.addFileToVFS = vi.fn();
    this.addFont = vi.fn();
    this.splitTextToSize = vi.fn(function(s){ return [s]; });
    this.lastAutoTable = { finalY: 40 };
    jspdfInstances.push(this);
  }
  return { jsPDF: FakeJsPDF };
});

vi.mock("jspdf-autotable", () => ({ default: vi.fn() }));

import { generateProgressReportPdf, buildProgressReportFileName } from "../utils/progressReportPdf";
import autoTable from "jspdf-autotable";

const REPORT = {
  success: true, report_type: "parent_progress_report", generated_at: "2026-08-08T10:00:00Z",
  child: { id: "child-1", name: "Aarav", grade: "Grade 10", board: "CBSE" },
  access_summary: { plan: { plan_name: "Free Tier", has_full_access: false }, feature_highlights: [] },
  progress_summary: { available: true, completed_chapters: 3, total_tracked: 5, recent_completions: [{ subject: "Science", chapter: "Ch1" }] },
  mock_test_summary: {
    available: true, tests_taken: 4, average_score: 62,
    subject_averages: { Science: 70, Maths: 55 },
    recent_tests: [{ subject: "Science", score: 70, date: "2026-08-01" }],
  },
  strengths: ["Science"],
  areas_for_improvement: [{ subject: "Maths", chapter: "Geometry" }],
  recommendations: [{ title: "Practice more mock tests" }],
  disclaimer: "Teacher-private notes and internal audit data are not included in this report.",
};

const EMPTY_REPORT = {
  ...REPORT,
  progress_summary: { available: false, completed_chapters: 0, total_tracked: 0, recent_completions: [] },
  mock_test_summary: { available: false, tests_taken: 0, average_score: null, subject_averages: {}, recent_tests: [] },
  strengths: [], areas_for_improvement: [], recommendations: [],
};

const REPORT_WITH_HINDI = {
  ...REPORT,
  strengths: ["विज्ञान"],
  areas_for_improvement: [{ subject: "Hindi", chapter: "अध्याय 12: भदंत आनंद कौसल्यायन" }],
};

beforeEach(() => {
  jspdfInstances.length = 0;
  autoTable.mockClear();
});

function lastDoc(){ return jspdfInstances[jspdfInstances.length - 1]; }

describe("buildProgressReportFileName", () => {
  test("builds a filename from child name and generated date", () => {
    expect(buildProgressReportFileName(REPORT)).toBe("Aarav_Progress_Report_2026-08-08.pdf");
  });

  test("falls back sanely when report is missing fields", () => {
    expect(buildProgressReportFileName({})).toMatch(/^student_Progress_Report_\d{4}-\d{2}-\d{2}\.pdf$/);
  });
});

describe("generateProgressReportPdf (generator-level)", () => {
  test("returns null and creates no PDF for a missing report", () => {
    var result = generateProgressReportPdf(null);
    expect(result).toBeNull();
    expect(jspdfInstances.length).toBe(0);
  });

  test("writes the child's name into the document", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    var wroteChildName = doc.text.mock.calls.some(function(args){
      return typeof args[0] === "string" && args[0].indexOf("Aarav") !== -1;
    });
    expect(wroteChildName).toBe(true);
  });

  test("saves with the expected filename", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    expect(doc.save).toHaveBeenCalledWith(buildProgressReportFileName(REPORT));
  });

  test("builds tables for progress, mock tests, and areas for improvement", () => {
    generateProgressReportPdf(REPORT);
    // recent_completions table + subject_averages table + recent_tests table + areas_for_improvement table = 4
    expect(autoTable).toHaveBeenCalledTimes(4);
    var bodies = autoTable.mock.calls.map(function(c){ return c[1].body; });
    var hasRecentTest = bodies.some(function(rows){
      return rows.some(function(row){ return row.indexOf("Science") !== -1 && row.indexOf("70%") !== -1; });
    });
    expect(hasRecentTest).toBe(true);
  });

  test("handles a report with no progress/mock-test data without crashing", () => {
    expect(function(){ generateProgressReportPdf(EMPTY_REPORT); }).not.toThrow();
    var doc = lastDoc();
    var wroteEmptyState = doc.text.mock.calls.some(function(args){
      return typeof args[0] === "string" && args[0].indexOf("No mock test data yet") !== -1;
    });
    expect(wroteEmptyState).toBe(true);
    expect(doc.save).toHaveBeenCalled();
  });

  test("includes the disclaimer text", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    var wroteDisclaimer = doc.text.mock.calls.some(function(args){
      var arg = args[0];
      var text = Array.isArray(arg) ? arg.join(" ") : arg;
      return typeof text === "string" && text.indexOf("Teacher-private notes") !== -1;
    });
    expect(wroteDisclaimer).toBe(true);
  });

  test("embeds the logo image top-left", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    expect(doc.addImage).toHaveBeenCalledTimes(1);
    var args = doc.addImage.mock.calls[0];
    expect(args[0]).toMatch(/^data:image\/png;base64,/);
    expect(args[1]).toBe("PNG");
    // x, y roughly top-left — small offset from the page margin, near the top
    expect(args[2]).toBeLessThanOrEqual(20);
    expect(args[3]).toBeLessThanOrEqual(20);
  });

  test("registers the embedded Devanagari font on every generated document", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    expect(doc.addFileToVFS).toHaveBeenCalledWith("NotoSansDevanagari.ttf", expect.any(String));
    expect(doc.addFont).toHaveBeenCalledWith("NotoSansDevanagari.ttf", "NotoSansDevanagari", "normal");
  });
});

describe("generateProgressReportPdf — Hindi content renders with the Devanagari font", () => {
  test("switches to the Devanagari font when writing Hindi text via doc.text", () => {
    generateProgressReportPdf(REPORT_WITH_HINDI);
    var doc = lastDoc();
    var switchedFont = doc.setFont.mock.calls.some(function(args){
      return args[0] === "NotoSansDevanagari" && args[1] === "normal";
    });
    expect(switchedFont).toBe(true);
  });

  test("does not use the Devanagari font for English-only reports", () => {
    generateProgressReportPdf(REPORT);
    var doc = lastDoc();
    var usedDevanagariFont = doc.setFont.mock.calls.some(function(args){
      return args[0] === "NotoSansDevanagari";
    });
    expect(usedDevanagariFont).toBe(false);
  });

  test("table cells with Hindi text get the Devanagari font via didParseCell, Latin cells don't", () => {
    generateProgressReportPdf(REPORT_WITH_HINDI);
    // areas_for_improvement table is the last autoTable call for this fixture
    var calls = autoTable.mock.calls;
    var areasCall = calls[calls.length - 1][1];
    expect(typeof areasCall.didParseCell).toBe("function");

    var hindiCell = { cell: { raw: "अध्याय 12: भदंत आनंद कौसल्यायन", styles: {} } };
    areasCall.didParseCell(hindiCell);
    expect(hindiCell.cell.styles.font).toBe("NotoSansDevanagari");

    var latinCell = { cell: { raw: "Hindi", styles: {} } };
    areasCall.didParseCell(latinCell);
    expect(latinCell.cell.styles.font).toBeUndefined();
  });
});

// ── Component-level: real workspace + real generator, through the button ────

vi.mock("../api/parentDashboard", () => ({
  getParentDashboardSummary: vi.fn(async () => ({
    success: true,
    parent: { id: "p1", username: "Parent" },
    parent_plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier", status_color: "restricted" },
    parent_canonical_plan_key: "FREE_TIER",
    child_limit: 1, children_count: 1, can_add_child: false,
    children: [{
      id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active",
      plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier", status_color: "restricted", description: "" },
      subscription: { canonical_plan_key: "FREE_TIER" },
      features: {}, feature_badges: [],
      mock_test_summary: { count: 4, average_score: 62, recent: [], free_daily_limit: 5 },
      activity_summary: { last_active: null, recent: [] },
      recommendations: [], notifications: [],
    }],
    notifications: [],
  })),
  getChildDetail: vi.fn(async () => ({
    success: true,
    child: { id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active" },
    plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier", description: "" },
    subscription: { canonical_plan_key: "FREE_TIER" },
    features: {}, feature_badges: [],
    progress: { available: false }, mock_tests: { available: false }, ai_activity: { available: false },
    recommendations: [], notifications: [],
  })),
  getChildAnalytics: vi.fn(async () => ({ success: true })),
  getChildAcademicInsights: vi.fn(async () => ({ success: true })),
  getChildProgressReport: vi.fn(async () => REPORT),
  getParentNotifications: vi.fn(async () => ({ success: true, source: "rule_based", unread_count: 0, total: 0, notifications: [] })),
  markNotificationRead: vi.fn(async () => ({ success: true })),
  markAllNotificationsRead: vi.fn(async () => ({ success: true, updated: 0 })),
  createStudent: vi.fn(async () => ({ success: true })),
  getParentSubscriptionPlans: vi.fn(async () => ({ success: true })),
  getFamily: vi.fn(async () => ({ success: true })),
  getParentChildren: vi.fn(async () => ({ success: true, children: [] })),
  getWeakAreaAlerts: vi.fn(async () => ({ success: true, alerts: [] })),
  inviteParent: vi.fn(async () => ({ success: true })),
}));

import ParentDashboardPage from "../pages/ParentDashboardPage";
const USER = { id: "p1", role: "parent", username: "Parent" };

describe("Download PDF button (component-level)", () => {
  test("clicking Download PDF on the Report tab drives the PDF generator through to jsPDF", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    document.querySelector("[data-testid='parent-child-status-card']").click();
    await waitFor(() => {
      expect(document.querySelector("[data-testid='parent-child-workspace']")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("ws-tab-report"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-section-report")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("download-pdf-btn"));

    await waitFor(() => {
      expect(jspdfInstances.length).toBeGreaterThan(0);
    });
    var doc = lastDoc();
    expect(doc.save).toHaveBeenCalledWith("Aarav_Progress_Report_2026-08-08.pdf");
  });
});

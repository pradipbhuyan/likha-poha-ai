/**
 * progressReportPdf.js
 * Builds a real, selectable-text PDF from the structured progress-report
 * payload (GET /api/parent/children/{id}/progress-report) — not a DOM
 * snapshot, so it stays crisp and avoids emoji/canvas-font rendering issues.
 *
 * Content can legitimately be in Hindi (chapter titles for the Hindi
 * subject) — jsPDF's built-in fonts only cover Latin/WinAnsi, so any
 * Devanagari text renders as garbage with them. A subset Noto Sans
 * Devanagari font (Latin + Devanagari glyphs) is embedded and swapped in
 * per-string/per-cell whenever the text contains Devanagari characters.
 */
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { NOTO_SANS_DEVANAGARI_BASE64 } from "./notoSansDevanagariFont";
import { REPORT_LOGO_PNG_BASE64 } from "./reportLogoImage";

var MARGIN_LEFT = 14;
var PAGE_BOTTOM = 270;
var TABLE_WIDTH = 180;
var DEVANAGARI_FONT = "NotoSansDevanagari";
var DEVANAGARI_RE = /[ऀ-ॿ]/;

function hasDevanagari(text){
  return DEVANAGARI_RE.test(String(text || ""));
}

function registerDevanagariFont(doc){
  doc.addFileToVFS("NotoSansDevanagari.ttf", NOTO_SANS_DEVANAGARI_BASE64);
  doc.addFont("NotoSansDevanagari.ttf", DEVANAGARI_FONT, "normal");
}

// Sets the right font for `text` before writing it — Devanagari content uses
// the embedded Unicode font (regular weight only), everything else keeps
// using Helvetica in the requested style.
function writeText(doc, text, x, y, style){
  if(hasDevanagari(text)){
    doc.setFont(DEVANAGARI_FONT, "normal");
  } else {
    doc.setFont("helvetica", style || "normal");
  }
  doc.text(text, x, y);
}

// jspdf-autotable hook: switch a cell's font to the Devanagari font if its
// raw text contains Devanagari characters, so table cells (chapter names
// etc.) render correctly regardless of which script the content is in.
function devanagariCellHook(data){
  if(hasDevanagari(data.cell.raw)){
    data.cell.styles.font = DEVANAGARI_FONT;
  }
}

function ensureSpace(doc, y, needed){
  if(y + needed > PAGE_BOTTOM){
    doc.addPage();
    return 20;
  }
  return y;
}

export function buildProgressReportFileName(report){
  var name = ((report && report.child && report.child.name) || "student").replace(/[^a-z0-9]/gi, "_");
  var date = ((report && report.generated_at) || "").slice(0, 10) || new Date().toISOString().slice(0, 10);
  return name + "_Progress_Report_" + date + ".pdf";
}

export function generateProgressReportPdf(report){
  if(!report) return null;

  var doc = new jsPDF();
  registerDevanagariFont(doc);

  var child = report.child || {};
  var plan = (report.access_summary || {}).plan || {};
  var progress = report.progress_summary || {};
  var mock = report.mock_test_summary || {};
  var strengths = report.strengths || [];
  var weakAreas = report.areas_for_improvement || [];
  var recs = report.recommendations || [];

  // ── Header: logo top-left + title ───────────────────────────────────────
  doc.addImage("data:image/png;base64," + REPORT_LOGO_PNG_BASE64, "PNG", MARGIN_LEFT, 10, 14, 14);
  var headerX = MARGIN_LEFT + 18;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Likha Poha AI - Progress Report", headerX, 17);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(100);
  var generatedDate = (report.generated_at || "").slice(0, 10) || new Date().toISOString().slice(0, 10);
  doc.text("Generated: " + generatedDate, headerX, 23);
  doc.setTextColor(0);
  var y = 32;

  doc.setFontSize(13);
  writeText(doc, child.name || "Student", MARGIN_LEFT, y, "bold");
  y += 6;
  doc.setFontSize(11);
  writeText(doc, (child.grade || "—") + " · " + (child.board || "CBSE"), MARGIN_LEFT, y, "normal");
  y += 9;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Access", MARGIN_LEFT, y);
  y += 6;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(
    (plan.plan_name || "Free Tier") + " — " + (plan.has_full_access ? "Full Access" : "Restricted Access"),
    MARGIN_LEFT, y
  );
  y += 10;

  // ── Progress ──────────────────────────────────────────────────────────────
  y = ensureSpace(doc, y, 20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Progress", MARGIN_LEFT, y);
  y += 6;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  if(progress.available){
    doc.text(
      progress.completed_chapters + " of " + progress.total_tracked + " chapters completed.",
      MARGIN_LEFT, y
    );
    y += 6;
    if((progress.recent_completions || []).length){
      autoTable(doc, {
        startY: y,
        head: [["Subject", "Chapter"]],
        body: progress.recent_completions.map(function(r){ return [r.subject || "", r.chapter || ""]; }),
        margin: { left: MARGIN_LEFT },
        styles: { fontSize: 9 },
        headStyles: { fillColor: [99, 102, 241] },
        didParseCell: devanagariCellHook,
      });
      y = doc.lastAutoTable.finalY + 8;
    }
  } else {
    doc.text("No progress data yet.", MARGIN_LEFT, y);
    y += 10;
  }

  // ── Mock tests ────────────────────────────────────────────────────────────
  y = ensureSpace(doc, y, 20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Mock Tests", MARGIN_LEFT, y);
  y += 6;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  if(mock.available){
    var avgLabel = mock.average_score != null ? mock.average_score + "%" : "—";
    doc.text(mock.tests_taken + " test(s) taken. Average score: " + avgLabel, MARGIN_LEFT, y);
    y += 6;

    var subjectRows = Object.keys(mock.subject_averages || {}).map(function(subj){
      return [subj, mock.subject_averages[subj] + "%"];
    });
    if(subjectRows.length){
      y = ensureSpace(doc, y, 16);
      autoTable(doc, {
        startY: y,
        head: [["Subject", "Average"]],
        body: subjectRows,
        margin: { left: MARGIN_LEFT },
        styles: { fontSize: 9 },
        headStyles: { fillColor: [99, 102, 241] },
        didParseCell: devanagariCellHook,
      });
      y = doc.lastAutoTable.finalY + 8;
    }

    if((mock.recent_tests || []).length){
      y = ensureSpace(doc, y, 16);
      autoTable(doc, {
        startY: y,
        head: [["Subject", "Score", "Date"]],
        body: mock.recent_tests.map(function(t){
          return [t.subject || "", t.score != null ? t.score + "%" : "—", t.date || ""];
        }),
        margin: { left: MARGIN_LEFT },
        styles: { fontSize: 9 },
        headStyles: { fillColor: [99, 102, 241] },
        didParseCell: devanagariCellHook,
      });
      y = doc.lastAutoTable.finalY + 8;
    }
  } else {
    doc.text("No mock test data yet.", MARGIN_LEFT, y);
    y += 10;
  }

  // ── Strengths ─────────────────────────────────────────────────────────────
  y = ensureSpace(doc, y, 16);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Strengths", MARGIN_LEFT, y);
  y += 6;
  doc.setFontSize(10);
  writeText(doc, strengths.length ? strengths.join(", ") : "No strong subjects identified yet.", MARGIN_LEFT, y, "normal");
  y += 10;

  // ── Areas for improvement ─────────────────────────────────────────────────
  y = ensureSpace(doc, y, 20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Areas for Improvement", MARGIN_LEFT, y);
  y += 6;
  if(weakAreas.length){
    autoTable(doc, {
      startY: y,
      head: [["Subject", "Chapter"]],
      body: weakAreas.map(function(a){ return [a.subject || "", a.chapter || ""]; }),
      margin: { left: MARGIN_LEFT },
      styles: { fontSize: 9 },
      headStyles: { fillColor: [99, 102, 241] },
      didParseCell: devanagariCellHook,
    });
    y = doc.lastAutoTable.finalY + 8;
  } else {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text("No specific weak areas identified yet.", MARGIN_LEFT, y);
    y += 10;
  }

  // ── Recommendations ───────────────────────────────────────────────────────
  y = ensureSpace(doc, y, 10);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Recommendations", MARGIN_LEFT, y);
  y += 6;
  doc.setFontSize(10);
  if(recs.length){
    recs.forEach(function(r){
      y = ensureSpace(doc, y, 6);
      writeText(doc, "- " + (r.title || ""), MARGIN_LEFT, y, "normal");
      y += 6;
    });
  } else {
    doc.setFont("helvetica", "normal");
    doc.text("No recommendations at this time.", MARGIN_LEFT, y);
    y += 6;
  }

  // ── Disclaimer ────────────────────────────────────────────────────────────
  y = ensureSpace(doc, y, 14);
  y += 4;
  doc.setFont("helvetica", "italic");
  doc.setFontSize(8);
  doc.setTextColor(120);
  doc.text(doc.splitTextToSize(report.disclaimer || "", TABLE_WIDTH), MARGIN_LEFT, y);
  doc.setTextColor(0);

  var filename = buildProgressReportFileName(report);
  doc.save(filename);
  return filename;
}

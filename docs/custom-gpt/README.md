# NLG Audit Checklist Auto-Filler — Custom GPT Setup Guide

## What This Does

This Custom GPT reads an audit voice transcript (or typed notes) and automatically fills the **"Non Agile - Audit Checklist"** tab of the NLG Internal Audit Delivery Review Checklist (CH-197 v2.3).

It produces:
- **Effectiveness Rating** (Column F): Very Low / Low / Medium / High / Not Applicable
- **Auditor's / Reviewer's Comment** (Column G): Factual, audit-language comment
- **Flag as Risk** (Column H): Yes / No
- **Finding Title** (Column B): Concise title for non-High findings

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `AUDIT_GPT_PART1_SYSTEM_PROMPT.md` | System prompt Part 1 — Purpose, rating definitions, checklist S.No 1–56 |
| `AUDIT_GPT_PART2_SYSTEM_PROMPT.md` | System prompt Part 2 — Checklist S.No 57–81, processing steps, output rules, glossary |
| `CHATGPT_INSTRUCTIONS.txt` | Combined plain-text version ready to paste into ChatGPT Custom GPT instructions field |
| `README.md` | This setup guide |

---

## How to Set Up the Custom GPT

### Step 1: Go to ChatGPT
1. Go to [https://chatgpt.com](https://chatgpt.com)
2. Click your profile → **My GPTs** → **Create a GPT**

### Step 2: Configure the GPT
Fill in these fields:

| Field | Value |
|-------|-------|
| **Name** | NLG Audit Checklist Filler |
| **Description** | Fills the Non Agile Audit Checklist from an audit voice transcript |
| **Instructions** | Paste the full contents of `CHATGPT_INSTRUCTIONS.txt` |
| **Conversation starters** | See suggestions below |

### Step 3: Suggested Conversation Starters
Add these as starter prompts in the GPT:
- "Here is my audit transcript. Please fill the Non Agile checklist."
- "I have a voice transcript from today's audit. Analyze and fill all 81 checklist items."
- "Update S.No [X] to [rating] based on new information."
- "Show me only the findings rated Very Low or Low."

### Step 4: Upload the Excel Template (Optional but Recommended)
Upload the file `NLG_InternalAuditDeliveryReviewChecklist_SLABased_July2026.xlsx` as a **Knowledge** file so the GPT has the exact original as context.

---

## How to Use the GPT

### Method 1: Paste Transcript Text
After the audit session, copy and paste your voice-to-text transcript directly into the chat:

```
Here is my audit transcript:

[paste your transcript here]

Please fill the Non Agile - Audit Checklist for this project.
```

### Method 2: Type Key Notes
If you don't have a full transcript, type bullet notes of what was discussed:

```
Project: XYZ Telecom Support
Phase: Steady State
- SOW is signed and valid until Dec 2026
- SPP is approved, operational process defined
- Risk register has 5 risks, 2 are overdue for closure
- No regression testing being done for maintenance changes
- SLA compliance is 98.2%, no breaches last quarter
- BCP drill was conducted in March 2025
- Team attrition is 25% this quarter (above org threshold)
- Previous DR finding on skill gap analysis is still open
```

### Method 3: Upload Audio Transcript File
If you have a `.txt` or `.docx` file of the transcribed audio, upload it directly to the chat.

---

## Understanding the Output

The GPT produces three sections:

### Section 1: Audit Summary
A paragraph summarizing project health, strengths, and key gaps.

### Section 2: Filled Checklist Table
A complete table with all 81 rows filled:

| S.No | Finding Title | Effectiveness Rating | Comment | Flag as Risk |
|------|--------------|---------------------|---------|-------------|

### Section 3: Top Findings
A prioritized list of the most critical findings (Very Low and Low ratings) with:
- What gap was found
- What was expected
- Recommended corrective action for the PM

---

## Copying Results to Excel

After the GPT fills the checklist:

1. Copy the table from the GPT response
2. Open the Excel file → go to **Non Agile - Audit Checklist** tab
3. For each row, fill:
   - **Column B** (Finding Title) — from GPT output
   - **Column F** (Effectiveness Rating) — from GPT output
   - **Column G** (Auditor's Comment) — from GPT output
   - **Column H** (Flag as Risk) — from GPT output

> Tip: Ask the GPT to "output only the rows with non-High ratings" to focus only on the findings that need manual entry.

---

## Making Corrections

You can instruct the GPT to update specific items:

- `"Change S.No 22 to High — the risk register is fully up to date"`
- `"Update S.No 48 — there are 2 open NCs from the last PMG review"`
- `"Mark S.No 34 as Not Applicable — no subcontractors on this project"`
- `"Re-show Part 3 top findings after all my corrections"`

---

## Effectiveness Rating Quick Reference

| Rating | When to Use |
|--------|------------|
| **Very Low** | Requirement completely absent / never implemented |
| **Low** | Isolated lapse or single failure |
| **Medium** | Potential gap / observation — risk if left unaddressed |
| **High** | Fully compliant and implemented |
| **Not Applicable** | Checkpoint irrelevant to this project/phase |

---

## Important Notes

- Comments are **mandatory** for Very Low, Low, and Medium ratings
- All Very Low and Low ratings are **automatically flagged as Risk = Yes**
- S.No 50, 51 → Mark **Not Applicable** unless it's a Medical/Telecom project
- S.No 78–81 → Mark **Not Applicable** unless the project is in closure phase
- S.No 72 → Mark **Not Applicable** for projects less than 2 years old
- S.No 23 and 43 → These are the auditor's own assessment — the GPT will analyze the overall picture to fill these

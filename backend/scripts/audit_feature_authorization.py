"""
audit_feature_authorization.py — Feature Authorization Audit
─────────────────────────────────────────────────────────────────────────────
Verifies that feature access matches the canonical feature matrix across all
plan/role/feature combinations. Designed to catch Free Tier premium leakage.

CLI:
  cd backend
  .venv/bin/python scripts/audit_feature_authorization.py
  .venv/bin/python scripts/audit_feature_authorization.py --sample
  .venv/bin/python scripts/audit_feature_authorization.py --all
  .venv/bin/python scripts/audit_feature_authorization.py --fail-critical
  .venv/bin/python scripts/audit_feature_authorization.py --json

Reports:
  reports/feature_authorization/feature_authorization_report.json
  reports/feature_authorization/feature_authorization_report.md
  reports/feature_authorization/feature_authorization_summary.csv
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.feature_authorization_service import Feature, authorize_feature
from app.services.subscription_resolver_service import resolve_user_subscription

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("audit_feature_authorization")

REPORT_DIR = Path("reports/feature_authorization")

# ── Canonical expected matrix ─────────────────────────────────────────────────
# Structure: (feature, plan_key) → expected_result
# "denied"  = access not allowed (allowed=False)
# "limited" = access allowed but limited
# "full"    = full access
# "admin_only" = only admin role has access regardless of plan

PAID_PLANS = {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
              "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT"}

EXPECTED_MATRIX: dict[tuple[str, str], str] = {}

def _build_expected_matrix():
    """Build the expected access matrix from the feature matrix definition."""
    from app.services.feature_authorization_service import _FEATURE_MATRIX
    for feature_key, config in _FEATURE_MATRIX.items():
        allowed_plans = config.get("allowed_plans")  # None = all plans
        limited_on = config.get("limited_on") or set()
        for plan in ["FREE_TIER", "NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                     "FAMILY_PREMIUM", "FAMILY_ANNUAL", "ADMIN_GRANT",
                     "EXPIRED_NANO", "EXPIRED_PREMIUM", "EXPIRED_FAMILY"]:
            effective = plan
            # Expired plans fall back to FREE_TIER
            if plan.startswith("EXPIRED_"):
                effective = "FREE_TIER"
            if allowed_plans is None:
                # Available to all
                if effective in limited_on:
                    EXPECTED_MATRIX[(feature_key, plan)] = "limited"
                else:
                    EXPECTED_MATRIX[(feature_key, plan)] = "full"
            elif effective in allowed_plans:
                EXPECTED_MATRIX[(feature_key, plan)] = "full"
            else:
                EXPECTED_MATRIX[(feature_key, plan)] = "denied"


# ── Synthetic user builder ────────────────────────────────────────────────────
# We never touch production users. All checks use in-memory synthetic user
# objects that match the shape expected by authorize_feature.

def _synthetic_user(plan_key: str, uid: str = "test-uid", has_parent_id: bool = False) -> dict:
    """Build a synthetic user dict for a given canonical plan key."""
    paid = plan_key in PAID_PLANS and not plan_key.startswith("EXPIRED_")
    return {
        "id": uid,
        "subscriptionPlan": plan_key.lower().replace("_", ""),
        "accessCbse": paid,
        "access_cbse": paid,
        "parentId": "parent-uid-1" if has_parent_id else None,
        "subscription_expires_at": None,
        "_test_plan_key": plan_key,  # used by mocked resolver
    }


# ── Audit check ───────────────────────────────────────────────────────────────

class AuditCheck:
    def __init__(self, feature: str, plan: str, scenario: str,
                 expected: str, actual: str, detail: str = ""):
        self.feature  = feature
        self.plan     = plan
        self.scenario = scenario
        self.expected = expected
        self.actual   = actual
        self.detail   = detail
        self.passed   = self._evaluate()
        self.severity = "critical" if not self.passed and expected in ("denied",) else (
                        "high" if not self.passed else "pass")

    def _evaluate(self) -> bool:
        if self.expected == self.actual:
            return True
        # "limited" and "full" are both acceptable for features that allow both
        if self.expected == "limited" and self.actual in ("limited", "full"):
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "feature": self.feature, "plan": self.plan, "scenario": self.scenario,
            "expected": self.expected, "actual": self.actual,
            "passed": self.passed, "severity": self.severity,
            "detail": self.detail[:200],
        }


# ── Core audit functions ──────────────────────────────────────────────────────

def _get_actual_access(feature_key: str, plan_key: str, monkeypatch_resolver=None) -> str:
    """
    Call authorize_feature with a synthetic user for the given plan and return
    "denied" | "limited" | "full".
    Uses in-process calls only — never hits production endpoints.
    """
    try:
        from app.services.feature_authorization_service import authorize_feature, _FEATURE_MATRIX
        import app.services.feature_authorization_service as feat_mod

        # Determine effective plan (expired plans → FREE_TIER)
        effective_plan = plan_key
        if plan_key.startswith("EXPIRED_"):
            effective_plan = "FREE_TIER"

        # Patch the resolver reference inside feature_authorization_service
        original_resolve = feat_mod.resolve_user_subscription

        def mock_resolve(uid, **kwargs):
            paid = effective_plan in PAID_PLANS
            return {
                "canonical_plan_key": effective_plan,
                "has_full_access": paid,
                "plan_name": effective_plan,
                "status": "active" if paid else "free",
                "expiring_soon": False,
                "days_remaining": None,
            }

        feat_mod.resolve_user_subscription = mock_resolve
        try:
            result = authorize_feature(user_id="test-uid", feature=feature_key)
        finally:
            feat_mod.resolve_user_subscription = original_resolve

        if not result.get("allowed", False):
            return "denied"
        if result.get("limited", False):
            return "limited"
        return "full"

    except Exception as e:
        return f"error:{str(e)[:50]}"


def _run_matrix_checks(features_to_check: list[str], plans_to_check: list[str]) -> list[AuditCheck]:
    """Run the full matrix of feature × plan checks."""
    checks = []
    for feature in features_to_check:
        for plan in plans_to_check:
            expected = EXPECTED_MATRIX.get((feature, plan), "unknown")
            if expected == "unknown":
                continue
            actual = _get_actual_access(feature, plan)
            check = AuditCheck(
                feature=feature, plan=plan,
                scenario=f"{feature} for {plan}",
                expected=expected, actual=actual,
                detail=f"Plan: {plan}, Feature: {feature}",
            )
            checks.append(check)
    return checks


def _run_scenario_checks() -> list[AuditCheck]:
    """
    Run high-risk scenario checks beyond the matrix.
    These test specific regression scenarios.
    """
    checks = []

    def scenario(feature, plan, scenario_name, expected, detail=""):
        actual = _get_actual_access(feature, plan)
        checks.append(AuditCheck(
            feature=feature, plan=plan, scenario=scenario_name,
            expected=expected, actual=actual, detail=detail,
        ))

    # Critical: Free Tier must NOT access premium features
    scenario(Feature.EXEMPLAR, "FREE_TIER",
             "New Free user cannot access Exemplar",
             "denied", "Critical regression: Free user must never see Exemplar")

    scenario(Feature.EXEMPLAR_RESEARCH, "FREE_TIER",
             "Free user cannot access Exemplar Research",
             "denied", "Free Tier must be denied Exemplar Research")

    scenario(Feature.FORMULA_SHEET_PREMIUM, "FREE_TIER",
             "Free user cannot expand Formula Sheet premium details",
             "denied", "Formula premium expansion must be paid-only")

    scenario(Feature.LESSON_DOWNLOAD, "FREE_TIER",
             "Free user cannot download lessons",
             "denied", "Lesson download is paid-only")

    scenario(Feature.MOCK_TEST_UNLIMITED, "FREE_TIER",
             "Free user cannot have unlimited mock tests",
             "denied", "5/day limit applies for Free Tier")

    # Paid plans MUST have full access
    for paid_plan in ["NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT"]:
        scenario(Feature.EXEMPLAR, paid_plan,
                 f"{paid_plan} can access Exemplar",
                 "full", f"Paid plan {paid_plan} must get full Exemplar access")
        scenario(Feature.FORMULA_SHEET_PREMIUM, paid_plan,
                 f"{paid_plan} can expand Formula Sheet",
                 "full", f"Paid plan {paid_plan} must get full Formula Sheet")

    # Expired plans MUST fall back to Free Tier
    scenario(Feature.EXEMPLAR, "EXPIRED_PREMIUM",
             "Expired Premium loses Exemplar access",
             "denied", "Expired plan must fall back to FREE_TIER restrictions")

    scenario(Feature.FORMULA_SHEET_PREMIUM, "EXPIRED_NANO",
             "Expired Nano loses Formula Sheet premium",
             "denied", "Expired Nano must fall back to FREE_TIER")

    # Mock Tests — limited (not denied) for Free Tier
    scenario(Feature.MOCK_TEST, "FREE_TIER",
             "Free user can take mock tests (limited)",
             "limited", "Mock tests allowed but limited to 5/day for Free Tier")

    # Ask Doubts — limited (not denied) for Free Tier
    scenario(Feature.ASK_DOUBTS, "FREE_TIER",
             "Free user can ask doubts (limited)",
             "limited", "Ask Doubts allowed but limited for Free Tier")

    # parentId alone must NOT grant paid access (covered by resolver but verify)
    # This is verified by checking FREE_TIER with parent_id set — should still be denied
    try:
        import app.services.feature_authorization_service as feat_mod2
        orig2 = feat_mod2.resolve_user_subscription
        def mock_free_with_parent(uid, **kw):
            return {"canonical_plan_key": "FREE_TIER", "has_full_access": False}
        feat_mod2.resolve_user_subscription = mock_free_with_parent
        try:
            result = feat_mod2.authorize_feature(user_id="child-with-parent", feature=Feature.EXEMPLAR)
            actual_with_parent = "denied" if not result.get("allowed") else "full"
        finally:
            feat_mod2.resolve_user_subscription = orig2
        checks.append(AuditCheck(
            feature=Feature.EXEMPLAR, plan="FREE_TIER_WITH_PARENT_ID",
            scenario="Child with parentId still denied Exemplar (parentId alone does not grant access)",
            expected="denied", actual=actual_with_parent,
            detail="parent_id alone must never grant paid access",
        ))
    except Exception as e:
        checks.append(AuditCheck(
            feature=Feature.EXEMPLAR, plan="FREE_TIER_WITH_PARENT_ID",
            scenario="parentId alone does not grant paid access",
            expected="denied", actual=f"error:{str(e)[:40]}",
            detail="Could not verify parentId check",
        ))

    return checks


# ── Scoring ───────────────────────────────────────────────────────────────────

def _compute_summary(checks: list[AuditCheck]) -> dict:
    total   = len(checks)
    passed  = sum(1 for c in checks if c.passed)
    failed  = total - passed
    critical = sum(1 for c in checks if not c.passed and c.severity == "critical")
    high    = sum(1 for c in checks if not c.passed and c.severity == "high")
    return {
        "total": total, "passed": passed, "failed": failed,
        "critical": critical, "high": high,
        "pass_rate": round(passed / max(total, 1) * 100, 1),
        "overall": "PASS" if failed == 0 else ("CRITICAL" if critical > 0 else "FAIL"),
    }


# ── Report writers ────────────────────────────────────────────────────────────

def _write_json(checks: list[AuditCheck], summary: dict, out_dir: Path) -> Path:
    p = out_dir / "feature_authorization_report.json"
    p.write_text(json.dumps({
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "checks": [c.to_dict() for c in checks],
        "failed_checks": [c.to_dict() for c in checks if not c.passed],
    }, indent=2), encoding="utf-8")
    _log.info("JSON report: %s", p)
    return p


def _write_markdown(checks: list[AuditCheck], summary: dict, out_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Feature Authorization Audit Report",
        "",
        f"_Generated: {ts} UTC_",
        "",
        f"**Overall:** {summary['overall']}",
        f"**Total checks:** {summary['total']}  **Passed:** {summary['passed']}  "
        f"**Failed:** {summary['failed']}  **Critical:** {summary['critical']}",
        f"**Pass rate:** {summary['pass_rate']}%",
        "",
        "---",
        "",
        "## Failed Checks",
        "",
    ]
    failed = [c for c in checks if not c.passed]
    if not failed:
        lines.append("_All checks passed._")
    else:
        lines.append("| Feature | Plan | Scenario | Expected | Actual | Severity |")
        lines.append("|---|---|---|---|---|---|")
        for c in failed:
            lines.append(f"| {c.feature} | {c.plan} | {c.scenario[:60]} | {c.expected} | {c.actual} | {c.severity} |")



def _write_markdown(checks, summary, out_dir):  # noqa: redefined by append
    pass  # replaced below


def _write_markdown_complete(checks, summary, out_dir):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Feature Authorization Audit Report",
        "",
        "_Generated: " + ts + " UTC_",
        "",
        "**Overall:** " + summary["overall"],
        "**Total:** " + str(summary["total"]) + "  Passed: " + str(summary["passed"]) +
        "  Failed: " + str(summary["failed"]) + "  Critical: " + str(summary["critical"]),
        "**Pass rate:** " + str(summary["pass_rate"]) + "%",
        "",
        "---",
        "",
        "## Failed Checks",
        "",
    ]
    failed = [c2 for c2 in checks if not c2.passed]
    if not failed:
        lines.append("_All checks passed._")
    else:
        lines += ["| Feature | Plan | Scenario | Expected | Actual | Severity |",
                  "|---|---|---|---|---|---|"]
        for c2 in failed:
            lines.append("| " + " | ".join([c2.feature, c2.plan, c2.scenario[:60],
                                             c2.expected, c2.actual, c2.severity]) + " |")
    lines += ["", "## Full Matrix", "", "| Feature | Plan | Expected | Actual | Status |",
              "|---|---|---|---|---|"]
    for c2 in checks:
        status = "PASS" if c2.passed else ("CRITICAL" if c2.severity == "critical" else "FAIL")
        lines.append("| " + " | ".join([c2.feature, c2.plan, c2.expected, c2.actual, status]) + " |")
    lines += ["", "---", "_Generated by audit_feature_authorization.py_"]
    p = out_dir / "feature_authorization_report.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _write_csv(checks, summary, out_dir):
    p = out_dir / "feature_authorization_summary.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["feature","plan","scenario","expected","actual","passed","severity","detail"])
        w.writeheader()
        for c2 in checks:
            w.writerow(c2.to_dict())
    return p


def run_audit(sample=False, fail_critical=False, output_json=False):
    _build_expected_matrix()

    all_features = [
        Feature.LESSONS, Feature.LESSON_DOWNLOAD,
        Feature.EXEMPLAR, Feature.EXEMPLAR_RESEARCH,
        Feature.MOCK_TEST, Feature.MOCK_TEST_UNLIMITED,
        Feature.ASK_DOUBTS, Feature.AI_ASSISTANT, Feature.AI_CHAT,
        Feature.FORMULA_SHEET_PREMIUM, Feature.QUESTION_BANK,
        Feature.PROGRESS_ANALYTICS,
    ]
    all_plans = ["FREE_TIER", "NANO", "PREMIUM", "FAMILY_PREMIUM", "ADMIN_GRANT",
                 "EXPIRED_NANO", "EXPIRED_PREMIUM", "EXPIRED_FAMILY"]

    if sample:
        all_features = all_features[:6]
        all_plans = ["FREE_TIER", "PREMIUM", "ADMIN_GRANT", "EXPIRED_PREMIUM"]

    _log.info("Running matrix checks (%d features x %d plans)...", len(all_features), len(all_plans))
    matrix_checks = _run_matrix_checks(all_features, all_plans)

    _log.info("Running scenario checks...")
    scenario_checks = _run_scenario_checks()

    all_checks = matrix_checks + scenario_checks
    summary = _compute_summary(all_checks)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(all_checks, summary, REPORT_DIR)
    _write_markdown_complete(all_checks, summary, REPORT_DIR)
    _write_csv(all_checks, summary, REPORT_DIR)

    if output_json:
        print(json.dumps({"summary": summary, "failed": [c.to_dict() for c in all_checks if not c.passed]}, indent=2))
    else:
        sep = "=" * 60
        print("")
        print(sep)
        print("FEATURE AUTHORIZATION AUDIT")
        print("  Overall   : " + summary["overall"])
        print("  Total     : " + str(summary["total"]))
        print("  Passed    : " + str(summary["passed"]))
        print("  Failed    : " + str(summary["failed"]))
        print("  Critical  : " + str(summary["critical"]))
        print("  Pass rate : " + str(summary["pass_rate"]) + "%")
        print("  Reports   : " + str(REPORT_DIR) + "/")
        print(sep)
        print("")

    if fail_critical and summary["critical"] > 0:
        _log.error("%d critical issue(s) found.", summary["critical"])
        sys.exit(1)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Feature Authorization Audit")
    parser.add_argument("--sample",        action="store_true", help="Quick sample audit")
    parser.add_argument("--all",           action="store_true", help="Full audit (default)")
    parser.add_argument("--fail-critical", action="store_true", help="Exit 1 on critical failures")
    parser.add_argument("--json",          action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()
    run_audit(sample=args.sample, fail_critical=args.fail_critical, output_json=args.json)


if __name__ == "__main__":
    main()

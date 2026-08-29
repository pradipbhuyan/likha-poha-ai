"""
test_school_service.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the principal-portal incentive tier ladder and school-code
generator (app/services/school_service.py). No payments/webhook dependency —
tier is a pure function of a paid-student count.
"""
from app.services.school_service import (
    SCHOOL_REWARD_CATALOG,
    SCHOOL_TIERS,
    compute_school_tier,
    generate_unique_school_code,
    next_tier_progress,
    rewards_unlocked_through,
)


class TestComputeSchoolTier:

    def test_zero_paid_students_is_bronze(self):
        assert compute_school_tier(0) == "bronze"

    def test_just_under_silver_threshold_is_bronze(self):
        assert compute_school_tier(99) == "bronze"

    def test_at_silver_threshold(self):
        assert compute_school_tier(100) == "silver"

    def test_between_silver_and_gold(self):
        assert compute_school_tier(250) == "silver"

    def test_at_gold_threshold(self):
        assert compute_school_tier(300) == "gold"

    def test_at_platinum_threshold(self):
        assert compute_school_tier(600) == "platinum"

    def test_well_above_platinum_stays_platinum(self):
        assert compute_school_tier(10_000) == "platinum"


class TestNextTierProgress:

    def test_progress_toward_silver(self):
        progress = next_tier_progress(40)
        assert progress == {"tier": "silver", "threshold": 100, "remaining": 60}

    def test_progress_toward_gold(self):
        progress = next_tier_progress(280)
        assert progress == {"tier": "gold", "threshold": 300, "remaining": 20}

    def test_no_progress_object_at_top_tier(self):
        assert next_tier_progress(600) is None
        assert next_tier_progress(999) is None

    def test_remaining_never_negative_at_exact_threshold(self):
        progress = next_tier_progress(100)
        assert progress["remaining"] == 200  # 100 paid students → silver, 200 to gold


class TestRewardCatalog:

    def test_every_tier_has_a_catalog_entry(self):
        for tier in SCHOOL_TIERS:
            assert tier in SCHOOL_REWARD_CATALOG

    def test_bronze_school_only_sees_bronze_rewards(self):
        unlocked = rewards_unlocked_through("bronze")
        keys = {r["key"] for r in unlocked}
        assert keys == {r["key"] for r in SCHOOL_REWARD_CATALOG["bronze"]}

    def test_gold_school_sees_bronze_silver_and_gold_rewards(self):
        unlocked = rewards_unlocked_through("gold")
        keys = {r["key"] for r in unlocked}
        expected = {
            r["key"]
            for tier in ("bronze", "silver", "gold")
            for r in SCHOOL_REWARD_CATALOG[tier]
        }
        assert keys == expected
        assert "platinum_dev_grant" not in keys

    def test_no_reward_is_a_personal_cash_payout(self):
        """
        Guardrail against regression toward a personal-commission model —
        every reward description should read as school-facing, never as
        cash paid to an individual.
        """
        for rewards in SCHOOL_REWARD_CATALOG.values():
            for reward in rewards:
                text = (reward["label"] + " " + reward["description"]).lower()
                assert "commission" not in text
                assert "cash payout" not in text


class TestGenerateUniqueSchoolCode:

    class _FakeTable:
        def __init__(self, existing_codes):
            self.existing_codes = existing_codes
            self._eq_value = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, _key, value):
            self._eq_value = value
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            from types import SimpleNamespace
            match = self._eq_value in self.existing_codes
            return SimpleNamespace(data=[{"id": "existing"}] if match else [])

    class _FakeClient:
        def __init__(self, existing_codes):
            self.existing_codes = existing_codes

        def table(self, _name):
            return TestGenerateUniqueSchoolCode._FakeTable(self.existing_codes)

    def test_code_uses_school_name_prefix(self):
        client = self._FakeClient(existing_codes=set())
        code = generate_unique_school_code("Sunrise Public School", client=client)
        assert code.startswith("SUN-")

    def test_falls_back_to_generic_prefix_for_non_alpha_name(self):
        client = self._FakeClient(existing_codes=set())
        code = generate_unique_school_code("123 456", client=client)
        assert code.startswith("SCH-")

    def test_retries_on_collision(self, monkeypatch):
        # Force the first two random suffixes to collide, third to succeed.
        calls = {"n": 0}

        def fake_suffix(length=5):
            calls["n"] += 1
            return "AAAAA" if calls["n"] <= 2 else "BBBBB"

        import app.services.school_service as school_service_module
        monkeypatch.setattr(school_service_module, "_random_suffix", fake_suffix)

        client = self._FakeClient(existing_codes={"SUN-AAAAA"})
        code = generate_unique_school_code("Sunrise", client=client)
        assert code == "SUN-BBBBB"

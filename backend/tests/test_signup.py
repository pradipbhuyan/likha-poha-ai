import hashlib
import hmac
import pytest
from app.routes import auth as auth_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_signature(order_id: str, payment_id: str, secret: str = "test-secret") -> str:
    """Generate a valid Razorpay-style HMAC-SHA256 signature for test payloads."""
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def fake_razorpay_order(plan_key="free"):
    """Return a fake Razorpay order response."""
    return {"id": f"order_{plan_key}_test123", "status": "created"}


def fake_auth_user(user_id="user-abc-123"):
    """Return a minimal fake Supabase auth user object."""
    class FakeUser:
        def __init__(self):
            self.id = user_id
    return FakeUser()


# ---------------------------------------------------------------------------
# signup-order endpoint tests
# ---------------------------------------------------------------------------

class TestSignupOrder:
    """Tests for POST /api/auth/signup-order (no auth required)."""

    def test_signup_order_fails_when_razorpay_not_configured(self, monkeypatch):
        """signup-order returns 503 when Razorpay keys are missing."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: False)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.create_signup_order(
                auth_module.SignupOrderRequest(email="user@test.com", plan_key="free")
            )
        assert exc.value.status_code == 503

    def test_signup_order_fails_for_invalid_plan(self, monkeypatch):
        """signup-order returns 400 when an unknown or hidden plan key is requested."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        # Mock the email-duplicate check so it returns no existing profile
        import unittest.mock as mock
        mock_execute = mock.MagicMock()
        mock_execute.data = []
        mock_chain = mock.MagicMock()
        mock_chain.execute.return_value = mock_execute
        mock_chain.limit.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        monkeypatch.setattr(auth_module.admin_client, "table", lambda _: mock_chain)
        monkeypatch.setattr(auth_module, "_get_plan", lambda plan_key: (_ for _ in ()).throw(
            __import__("fastapi").HTTPException(status_code=400, detail="Invalid plan selected.")
        ))

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.create_signup_order(
                auth_module.SignupOrderRequest(email="user@test.com", plan_key="nonexistent")
            )
        assert exc.value.status_code == 400

    def test_signup_order_succeeds_for_valid_trial_plan(self, monkeypatch):
        """signup-order creates a Razorpay order for the Try It Out (free) plan."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        # Mock the email-duplicate check so it returns no existing profile
        import unittest.mock as mock
        mock_execute = mock.MagicMock()
        mock_execute.data = []
        mock_chain = mock.MagicMock()
        mock_chain.execute.return_value = mock_execute
        mock_chain.limit.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        monkeypatch.setattr(auth_module.admin_client, "table", lambda _: mock_chain)
        monkeypatch.setattr(auth_module, "_get_plan", lambda plan_key: {
            "key": "free", "price": 100, "discount_percent": 0,
            "label": "Try It Out", "billing_label": "14 days", "is_public": True,
        })
        monkeypatch.setattr(auth_module, "_plan_amount", lambda plan: 100)

        class FakeResp:
            status_code = 200
            def json(self):
                return fake_razorpay_order("free")

        with mock.patch("app.routes.auth.settings") as mock_settings:
            mock_settings.RAZORPAY_KEY_ID = "rzp_test_key"
            mock_settings.RAZORPAY_KEY_SECRET = "rzp_test_secret"
            import requests
            with mock.patch.object(requests, "post", return_value=FakeResp()):
                result = auth_module.create_signup_order(
                    auth_module.SignupOrderRequest(email="parent@test.com", plan_key="free")
                )
        assert result["success"] is True
        assert result["amount"] == 100
        assert result["currency"] == "INR"
        assert "order_id" in result

    def test_signup_order_succeeds_for_standard_plan(self, monkeypatch):
        """signup-order creates a Razorpay order for the Standard (starter) plan."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        # Mock the email-duplicate check so it returns no existing profile
        import unittest.mock as mock
        mock_execute = mock.MagicMock()
        mock_execute.data = []
        mock_chain = mock.MagicMock()
        mock_chain.execute.return_value = mock_execute
        mock_chain.limit.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        monkeypatch.setattr(auth_module.admin_client, "table", lambda _: mock_chain)
        monkeypatch.setattr(auth_module, "_get_plan", lambda plan_key: {
            "key": "starter", "price": 299, "discount_percent": 0,
            "label": "Standard", "billing_label": "month", "is_public": True,
        })
        monkeypatch.setattr(auth_module, "_plan_amount", lambda plan: 299)

        class FakeResp:
            status_code = 200
            def json(self):
                return {"id": "order_starter_456", "status": "created"}

        with mock.patch("app.routes.auth.settings") as mock_settings:
            mock_settings.RAZORPAY_KEY_ID = "rzp_test_key"
            mock_settings.RAZORPAY_KEY_SECRET = "rzp_test_secret"
            import requests
            with mock.patch.object(requests, "post", return_value=FakeResp()):
                result = auth_module.create_signup_order(
                    auth_module.SignupOrderRequest(email="student@test.com", plan_key="starter")
                )
        assert result["success"] is True
        assert result["amount"] == 299


# ---------------------------------------------------------------------------
# complete-signup endpoint tests
# ---------------------------------------------------------------------------

class TestCompleteSignup:
    """Tests for POST /api/auth/complete-signup (parent, student, teacher journeys)."""

    BASE_PAYLOAD = dict(
        plan_key="free",
        razorpay_order_id="order_test_001",
        razorpay_payment_id="pay_test_001",
        razorpay_signature="valid_sig",
    )

    def _mock_dependencies(self, monkeypatch, existing_email=False):
        """Set up standard monkeypatches for complete-signup tests."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        monkeypatch.setattr(auth_module, "_verify_signature", lambda *_: True)
        monkeypatch.setattr(auth_module, "_get_plan", lambda plan_key: {
            "key": "free", "price": 100, "discount_percent": 0, "is_public": True,
            "access_cbse": True, "access_sof_science": False, "access_sof_maths": False,
            "access_sof_english": False, "daily_token_limit": 50000, "monthly_token_limit": 1000000,
        })
        monkeypatch.setattr(auth_module, "_plan_amount", lambda plan: 100)
        monkeypatch.setattr(auth_module, "_profile_access_fields", lambda plan: {
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": True, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "daily_token_limit": 50000, "monthly_token_limit": 1000000,
        })

        # Mock Supabase admin_client
        class FakeQueryBuilder:
            def __init__(self, data=None):
                self._data = data or []
            def table(self, *_): return self
            def select(self, *_): return self
            def eq(self, *_): return self
            # Only .eq() (the email-uniqueness check below) should see
            # existing_email's canned data. .ilike() is _reject_taken_username's
            # username-uniqueness check — a different column — and none of
            # these tests simulate a username collision, so it always reads empty.
            def ilike(self, *_): return FakeQueryBuilder()
            def limit(self, *_): return self
            def insert(self, *_): return self
            def upsert(self, *_, **__): return self
            def execute(self):
                class R:
                    data = []
                if self._data:
                    class R2:
                        data = self._data
                    return R2()
                return R()

        fake_client = FakeQueryBuilder(
            data=[{"id": "existing-user"}] if existing_email else []
        )
        monkeypatch.setattr(auth_module, "admin_client", fake_client)

    # ------------------------------------------------------------------
    # PARENT signup journey
    # ------------------------------------------------------------------

    def test_parent_signup_creates_account_and_family(self, monkeypatch):
        """
        Happy path: parent signs up, account is created with a family record.
        Profile role must be 'parent' and success must be True.
        """
        self._mock_dependencies(monkeypatch)

        captured_profile = {}
        captured_family = {}

        class FamilyCapture:
            def table(self, name):
                self._tbl = name
                return self
            def select(self, *_): return self
            def eq(self, *_): return self
            def ilike(self, *_): return self
            def limit(self, *_): return self
            def insert(self, data):
                if self._tbl == "families":
                    captured_family.update(data)
                    class R:
                        data = [{"id": "family-001"}]
                    return type("R", (), {"execute": lambda self: type("D", (), {"data": [{"id": "family-001"}]})()})()
                captured_profile.update(data)
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def upsert(self, *_, **__):
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def execute(self):
                class R:
                    data = []
                return R()

        monkeypatch.setattr(auth_module, "admin_client", FamilyCapture())

        def fake_invite(email, username):
            return fake_auth_user("parent-user-123")

        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("fake-id-001"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="parent",
            name="Priya Menon",
            email="priya@test.com",
            **self.BASE_PAYLOAD,
        ))
        assert result["success"] is True
        assert result["role"] == "parent"
        assert "email" in result["message"].lower() or "account" in result["message"].lower()

    def test_parent_signup_rejects_duplicate_email(self, monkeypatch):
        """complete-signup returns 409 when the email already has an account."""
        self._mock_dependencies(monkeypatch, existing_email=True)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.complete_signup(auth_module.CompleteSignupRequest(
                role="parent",
                name="Priya Menon",
                email="existing@test.com",
                **self.BASE_PAYLOAD,
            ))
        assert exc.value.status_code == 409
        assert "already exists" in exc.value.detail

    def test_complete_signup_rejects_taken_username(self, monkeypatch):
        """
        complete-signup returns 409 when the username is already taken by a
        different profile — even if the email is unique.

        Regression for the "likha" incident (2026-08-20): get_child_analytics
        and get_parent_dashboard_summary filter test_history/student_progress
        by the username STRING, not the profile id, so two profiles sharing a
        username silently read each other's mock test scores and progress.
        See docs/sql/2026-08-16_check_username_uniqueness.sql.
        """
        self._mock_dependencies(monkeypatch)

        class TakenUsernameClient:
            def table(self, *_): return self
            def select(self, *_): return self
            def eq(self, *_): return self       # email-uniqueness check: not a collision
            def ilike(self, *_): return self     # username-uniqueness check: IS a collision
            def limit(self, *_): return self
            def execute(self):
                class R:
                    data = [{"id": "some-other-profile"}]
                return R()

        monkeypatch.setattr(auth_module, "admin_client", TakenUsernameClient())

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.complete_signup(auth_module.CompleteSignupRequest(
                role="parent",
                name="likha",
                email="newparent@test.com",
                **self.BASE_PAYLOAD,
            ))
        assert exc.value.status_code == 409
        assert "already taken" in exc.value.detail.lower()

    # ------------------------------------------------------------------
    # STUDENT signup journey
    # ------------------------------------------------------------------

    def test_student_signup_stores_grade(self, monkeypatch):
        """Happy path: student signs up with Grade 9, profile stores grade and board."""
        self._mock_dependencies(monkeypatch)
        captured = {}

        class StudentCapture:
            def table(self, name):
                self._tbl = name
                return self
            def select(self, *_): return self
            def eq(self, *_): return self
            def ilike(self, *_): return self
            def limit(self, *_): return self
            def insert(self, data):
                captured.update(data)
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def upsert(self, *_, **__):
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def execute(self):
                class R:
                    data = []
                return R()

        monkeypatch.setattr(auth_module, "admin_client", StudentCapture())
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("student-001"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="student",
            name="Akshita Sharma",
            email="akshita@test.com",
            grade="Grade 9",
            **self.BASE_PAYLOAD,
        ))
        assert result["success"] is True
        assert result["role"] == "student"

    def test_student_signup_defaults_to_grade_9_for_invalid_grade(self, monkeypatch):
        """Student signup with an out-of-range grade defaults to Grade 9."""
        self._mock_dependencies(monkeypatch)
        captured = {}

        class GradeCapture:
            def table(self, name):
                self._tbl = name
                return self
            def select(self, *_): return self
            def eq(self, *_): return self
            def ilike(self, *_): return self
            def limit(self, *_): return self
            def insert(self, data):
                captured.update(data)
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def upsert(self, *_, **__):
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def execute(self):
                class R:
                    data = []
                return R()

        monkeypatch.setattr(auth_module, "admin_client", GradeCapture())
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("student-002"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="student",
            name="Rohan Test",
            email="rohan@test.com",
            grade="Grade 99",  # not in valid set (Grade 1-12 are all valid now)
            **self.BASE_PAYLOAD,
        ))
        assert result["success"] is True
        # Grade stored in captured profile should be Grade 9 (default)
        assert captured.get("grade") == "Grade 9"

    # ------------------------------------------------------------------
    # TEACHER signup journey
    # ------------------------------------------------------------------

    def test_teacher_signup_stores_school_name(self, monkeypatch):
        """Happy path: teacher signs up with school name stored in profile."""
        self._mock_dependencies(monkeypatch)
        captured = {}

        class TeacherCapture:
            def table(self, name):
                self._tbl = name
                return self
            def select(self, *_): return self
            def eq(self, *_): return self
            def ilike(self, *_): return self
            def limit(self, *_): return self
            def insert(self, data):
                captured.update(data)
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def upsert(self, *_, **__):
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def execute(self):
                class R:
                    data = []
                return R()

        monkeypatch.setattr(auth_module, "admin_client", TeacherCapture())
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("teacher-001"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="teacher",
            name="Mr. Ramesh Kumar",
            email="ramesh@school.com",
            school="Delhi Public School",
            **self.BASE_PAYLOAD,
        ))
        assert result["success"] is True
        assert result["role"] == "teacher"
        assert captured.get("school_name") == "Delhi Public School"

    def test_teacher_signup_without_school_name_still_succeeds(self, monkeypatch):
        """Teacher signup without school name is allowed (optional field)."""
        self._mock_dependencies(monkeypatch)
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("teacher-002"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="teacher",
            name="Ms. Ananya Iyer",
            email="ananya@school.com",
            school=None,
            **self.BASE_PAYLOAD,
        ))
        assert result["success"] is True
        assert result["role"] == "teacher"

    # ------------------------------------------------------------------
    # Error scenarios
    # ------------------------------------------------------------------

    def test_complete_signup_rejects_invalid_role(self, monkeypatch):
        """complete-signup returns 400 for an unrecognised role."""
        self._mock_dependencies(monkeypatch)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.complete_signup(auth_module.CompleteSignupRequest(
                role="admin",   # not allowed via public signup
                name="Hack Attempt",
                email="hack@test.com",
                **self.BASE_PAYLOAD,
            ))
        assert exc.value.status_code == 400
        assert "invalid role" in exc.value.detail.lower()

    def test_complete_signup_rejects_bad_payment_signature(self, monkeypatch):
        """complete-signup returns 400 when the Razorpay signature does not verify."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        monkeypatch.setattr(auth_module, "_verify_signature", lambda *_: False)
        monkeypatch.setattr(auth_module, "_get_plan", lambda pk: {
            "key": "free", "price": 100, "discount_percent": 0, "is_public": True,
            "access_cbse": True, "access_sof_science": False, "access_sof_maths": False,
            "access_sof_english": False, "daily_token_limit": 50000, "monthly_token_limit": 1000000,
        })

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.complete_signup(auth_module.CompleteSignupRequest(
                role="parent",
                name="Tampered User",
                email="tamper@test.com",
                plan_key="free",
                razorpay_order_id="order_x",
                razorpay_payment_id="pay_x",
                razorpay_signature="bad_signature",
            ))
        assert exc.value.status_code == 400
        assert "verification failed" in exc.value.detail.lower()

    def test_complete_signup_rejects_when_payment_not_configured(self, monkeypatch):
        """complete-signup returns 503 when Razorpay is not configured."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: False)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            auth_module.complete_signup(auth_module.CompleteSignupRequest(
                role="parent",
                name="No Payment",
                email="nopay@test.com",
                **self.BASE_PAYLOAD,
            ))
        assert exc.value.status_code == 503

    def test_complete_signup_family_plan_creates_parent_account(self, monkeypatch):
        """Family plan signup creates a parent account with higher limits."""
        monkeypatch.setattr(auth_module, "_razorpay_is_configured", lambda: True)
        monkeypatch.setattr(auth_module, "_verify_signature", lambda *_: True)
        monkeypatch.setattr(auth_module, "_get_plan", lambda plan_key: {
            "key": "family_premium", "price": 499, "discount_percent": 0,
            "is_public": True, "access_cbse": True, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "daily_token_limit": 150000, "monthly_token_limit": 5000000,
        })
        monkeypatch.setattr(auth_module, "_plan_amount", lambda plan: 499)
        monkeypatch.setattr(auth_module, "_profile_access_fields", lambda plan: {
            "subscription_plan": "family_premium", "account_status": "active",
            "access_cbse": True, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "daily_token_limit": 150000, "monthly_token_limit": 5000000,
        })

        class FamilyClient:
            def table(self, name):
                self._tbl = name
                return self
            def select(self, *_): return self
            def eq(self, *_): return self
            def ilike(self, *_): return self
            def limit(self, *_): return self
            def insert(self, data):
                if self._tbl == "families":
                    return type("R", (), {"execute": lambda self: type("D", (), {"data": [{"id": "fam-002"}]})()})()
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def upsert(self, *_, **__):
                return type("R", (), {"execute": lambda self: type("D", (), {"data": []})()})()
            def execute(self):
                class R:
                    data = []
                return R()

        monkeypatch.setattr(auth_module, "admin_client", FamilyClient())
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda email, password, email_confirm=True: fake_auth_user("family-parent-001"),
            raising=False,
        )

        result = auth_module.complete_signup(auth_module.CompleteSignupRequest(
            role="parent",
            name="Sharma Family",
            email="family@test.com",
            plan_key="family_premium",
            razorpay_order_id="order_family_001",
            razorpay_payment_id="pay_family_001",
            razorpay_signature="valid_sig",
        ))
        assert result["success"] is True
        assert result["role"] == "parent"


# ---------------------------------------------------------------------------
# Signature verification unit tests
# ---------------------------------------------------------------------------

class TestSignatureVerification:
    """Unit tests for the HMAC-SHA256 Razorpay signature helper."""

    def test_valid_signature_passes(self, monkeypatch):
        """A correctly computed signature returns True."""
        import unittest.mock as mock
        with mock.patch("app.routes.auth.settings") as s:
            s.RAZORPAY_KEY_SECRET = "test-secret-123"
            sig = make_valid_signature("order_abc", "pay_xyz", "test-secret-123")
            assert auth_module._verify_signature("order_abc", "pay_xyz", sig) is True

    def test_wrong_signature_fails(self, monkeypatch):
        """A tampered signature returns False."""
        import unittest.mock as mock
        with mock.patch("app.routes.auth.settings") as s:
            s.RAZORPAY_KEY_SECRET = "test-secret-123"
            assert auth_module._verify_signature("order_abc", "pay_xyz", "wrong_sig") is False

    def test_empty_signature_fails(self, monkeypatch):
        """An empty signature string returns False."""
        import unittest.mock as mock
        with mock.patch("app.routes.auth.settings") as s:
            s.RAZORPAY_KEY_SECRET = "test-secret-123"
            assert auth_module._verify_signature("order_abc", "pay_xyz", "") is False

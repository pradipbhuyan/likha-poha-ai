import hashlib
import hmac

import pytest
from fastapi import HTTPException

import app.routes.payments as payments_route


def test_create_payment_order_returns_503_when_razorpay_is_not_configured(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", None)
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", None)

    request = payments_route.CreatePaymentOrderRequest(
        child_id="child-1",
        plan_key="starter",
    )

    with pytest.raises(HTTPException) as error:
        payments_route.create_payment_order(
            request,
            parent={"profile": {"id": "parent-1", "family_id": "family-1"}},
        )

    assert error.value.status_code == 503
    assert "Payment gateway is not configured" in error.value.detail


def test_create_payment_order_uses_discounted_plan_amount(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(
        payments_route,
        "get_child_by_id",
        lambda parent_id, child_id: {
            "id": child_id,
            "family_id": "family-1",
            "role": "student",
        },
    )
    monkeypatch.setattr(
        payments_route,
        "get_public_plan",
        lambda plan_key: {
            "key": plan_key,
            "label": "Standard",
            "price": 499,
            "discount_percent": 10,
            "discount_label": "Summer Special",
            "is_public": True,
        },
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        captured["notes"] = notes
        return {
            "id": "order_123",
            "amount": amount_paise,
            "currency": "INR",
        }

    monkeypatch.setattr(
        payments_route,
        "create_razorpay_order",
        fake_create_razorpay_order,
    )
    monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)

    result = payments_route.create_payment_order(
        payments_route.CreatePaymentOrderRequest(
            child_id="child-1",
            plan_key="starter",
        ),
        parent={"profile": {"id": "parent-1", "family_id": "family-1"}},
    )

    assert result["success"] is True
    assert captured["amount_paise"] == 44900
    assert captured["notes"]["plan_key"] == "starter"
    assert result["payment"]["amount"] == 449


def test_verify_payment_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(
        payments_route,
        "get_payment_by_order_id",
        lambda order_id: {
            "razorpay_order_id": order_id,
            "parent_id": "parent-1",
            "child_id": "child-1",
            "plan_key": "starter",
            "status": "created",
        },
    )
    monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)

    with pytest.raises(HTTPException) as error:
        payments_route.verify_payment(
            payments_route.VerifyPaymentRequest(
                razorpay_order_id="order_123",
                razorpay_payment_id="pay_123",
                razorpay_signature="bad-signature",
            ),
            parent={"profile": {"id": "parent-1", "family_id": "family-1"}},
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Payment verification failed."


def test_verify_payment_activates_plan_after_signature_match(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    order_id = "order_123"
    payment_id = "pay_123"
    signature = hmac.new(
        b"secret",
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    payment = {
        "razorpay_order_id": order_id,
        "parent_id": "parent-1",
        "child_id": "child-1",
        "plan_key": "starter",
        "status": "created",
    }
    plan = {
        "key": "starter",
        "label": "Standard",
        "is_public": True,
    }

    monkeypatch.setattr(payments_route, "get_payment_by_order_id", lambda _order: payment)
    monkeypatch.setattr(payments_route, "get_public_plan", lambda _plan: plan)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)
    monkeypatch.setattr(
        payments_route,
        "activate_plan_for_payment",
        lambda _payment, _plan, _parent: [{"id": "child-1", "subscription_plan": "starter"}],
    )

    result = payments_route.verify_payment(
        payments_route.VerifyPaymentRequest(
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        ),
        parent={"profile": {"id": "parent-1", "family_id": "family-1"}},
    )

    assert result["success"] is True
    assert result["payment"]["status"] == "paid"
    assert result["payment"]["razorpay_payment_id"] == payment_id
    assert result["activated_profiles"][0]["subscription_plan"] == "starter"

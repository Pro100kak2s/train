from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():

    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert body["message"] == (
        "ml churn service is running"
    )


def test_train_endpoint():

    response = client.post(
        "/model/train",
        json={
            "model_type": "logreg"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert "accuracy" in body

    assert "f1" in body

    assert isinstance(
        body["accuracy"],
        float
    )

    assert isinstance(
        body["f1"],
        float
    )


def test_status_endpoint():

    client.post(
        "/model/train",
        json={
            "model_type": "logreg"
        }
    )

    response = client.get(
        "/model/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["is_trained"] is True

    assert body["model_type"] == "logreg"

    assert body["metrics"] is not None


def test_predict_endpoint():

    client.post(
        "/model/train",
        json={
            "model_type": "logreg"
        }
    )

    response = client.post(
        "/predict",
        json={
            "monthly_fee": 29.99,
            "usage_hours": 30,
            "support_requests": 1,
            "account_age_months": 12,
            "failed_payments": 0,
            "region": "europe",
            "device_type": "mobile",
            "payment_method": "card",
            "autopay_enabled": 1
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert "prediction" in body

    assert "probability_stay" in body

    assert "probability_churn" in body

    assert body["prediction"] in [0, 1]

    assert isinstance(
        body["probability_stay"],
        float
    )

    assert isinstance(
        body["probability_churn"],
        float
    )
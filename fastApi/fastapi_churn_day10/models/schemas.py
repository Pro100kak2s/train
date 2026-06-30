from __future__ import annotations

from pydantic import BaseModel, Field

from typing import Any

class FeatureVectorChurn(BaseModel):
    monthly_fee: float
    usage_hours: float
    support_requests: int
    account_age_months: int
    failed_payments: int
    region: str
    device_type: str
    payment_method: str
    autopay_enabled: int
    model_config = {
        "json_schema_extra": {
            "example": {
                "monthly_fee": 29.99,
                "usage_hours": 35.5,
                "support_requests": 1,
                "account_age_months": 12,
                "failed_payments": 0,
                "region": "europe",
                "device_type": "mobile",
                "payment_method": "card",
                "autopay_enabled": 1
            }
        }
    }


class DatasetRowChurn(BaseModel):
    monthly_fee: float
    usage_hours: float
    support_requests: int
    account_age_months: int
    failed_payments: int
    region: str
    device_type: str
    payment_method: str
    autopay_enabled: int
    churn: int

class PredictionResponseChurn(BaseModel):
    prediction: int
    probability_stay: float
    probability_churn: float

class TrainingConfigChurn(BaseModel):
    model_type: str

    hyperparameters: dict[str, Any] = Field(
        default_factory=dict
    )

from typing import Any

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Any | None = None
from __future__ import annotations
from logging_config import logger

from fastapi import FastAPI
from fastapi import Request

from fastapi.responses import JSONResponse

from fastapi.exceptions import (
    RequestValidationError
)

from fastApi.fastapi_churn_day13.services.dataset_service import DatasetService

from fastApi.fastapi_churn_day13.models.schemas import (
    FeatureVectorChurn,
    PredictionResponseChurn,
    TrainingConfigChurn,
    ErrorResponse
)

app = FastAPI()

dataset_service = DatasetService()

dataset_service.load_churn_model()


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request,
    exc: ValueError
):
    logger.error(
        f"Business error: {exc}"
    )

    return JSONResponse(
        status_code=400,
        content={
            "code": "BAD_REQUEST",
            "message": str(exc),
            "details": None
        }
    )


@app.exception_handler(
    RequestValidationError
)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
):
    logger.error(
        f"Validation error: {exc.errors()}"
    )

    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.get("/")
def root():
    return {
        "message": "ml churn service is running"
    }


@app.post(
    "/predict",
    response_model=PredictionResponseChurn,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Prediction error"
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation error"
        }
    }
)
def predict(
    features: FeatureVectorChurn
):
    return dataset_service.predict_churn(
        features.model_dump()
    )


@app.get("/dataset/preview")
def dataset_preview(
    rows: int = 5
):
    return dataset_service.get_preview(
        rows
    ).to_dict(
        orient="records"
    )


@app.get("/dataset/info")
def dataset_info():
    return dataset_service.get_info()


@app.get("/dataset/split-info")
def dataset_split_info():
    return dataset_service.get_split_info()


@app.post(
    "/model/train",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Training error"
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation error"
        }
    }
)
def train_model(
    config: TrainingConfigChurn
):
    return dataset_service.train_churn_model(
        config
    )

@app.get("/model/status")
def model_status():
    return dataset_service.get_model_status()

@app.get("/health")
def health():
    return dataset_service.get_health()

@app.get("/model/schema")
def model_schema():
    return dataset_service.get_model_schema()

@app.get("/model/metrics")
def model_metrics(
    model_type: str | None = None
):
    return dataset_service.get_metrics(
        model_type
    )

logger.info(
    "Application started"
)
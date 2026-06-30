from fastapi import FastAPI

from models.schemas import (
    FeatureVectorChurn,
)
from services.dataset_service import DatasetService


app = FastAPI()

dataset_service = DatasetService()


@app.get("/")
def root():
    return {
        "message": "ml churn service is running"
    }


@app.post("/predict")
def predict(features: FeatureVectorChurn):
    return features


@app.get("/dataset/preview")
def dataset_preview(rows: int = 5):
    return dataset_service.get_preview(
        rows
    ).to_dict(
        orient="records"
    )


@app.get("/dataset/info")
def dataset_info():
    return dataset_service.get_info()
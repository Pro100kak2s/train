from fastapi import FastAPI

from models.schemas import (
    FeatureVectorChurn,
)
from services.dataset_service import DatasetService


app = FastAPI()

dataset_service = DatasetService()

dataset_service.load_churn_model()

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

    try:
        return dataset_service.get_preview(
            rows
        ).to_dict(
            orient="records"
        )

    except ValueError as error:
        return {
            "error": str(error)
        }


@app.get("/dataset/info")
def dataset_info():
    try:
        return dataset_service.get_info()
    except ValueError as error:
        return {
            "error": str(error)
        }


@app.get("/dataset/split-info")
def dataset_split_info():
   try:
       return dataset_service.get_split_info()
   except ValueError as error:
       return {
           "error": str(error)
       }

@app.post("/model/train")
def train_model():

    try:
        return dataset_service.train_churn_model()

    except Exception as error:

        return {
            "error": str(error)
        }

@app.get("/model/status")
def model_status():
    return dataset_service.get_model_status()

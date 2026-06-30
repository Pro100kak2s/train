import pandas as pd
import joblib
import os

from datetime import datetime

from sklearn.model_selection import train_test_split

from sklearn.compose import ColumnTransformer

from sklearn.pipeline import Pipeline

from models.schemas import (
    TrainingConfigChurn
)

from sklearn.preprocessing import (
    StandardScaler,
    OneHotEncoder
)

from sklearn.ensemble import (
    RandomForestClassifier
)

from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    f1_score
)

class DatasetService:

    def __init__(self):
        try:
            self.df = pd.read_csv("data/churn_dataset.csv")
        except FileNotFoundError:
            self.df = None

        self.numeric_features = [
            "monthly_fee",
            "usage_hours",
            "support_requests",
            "account_age_months",
            "failed_payments",
            "autopay_enabled"
        ]

        self.categorical_features = [
            "region",
            "device_type",
            "payment_method"
        ]

        self.feature_columns = [
            "monthly_fee",
            "usage_hours",
            "support_requests",
            "account_age_months",
            "failed_payments",
            "region",
            "device_type",
            "payment_method",
            "autopay_enabled"
        ]

        self.model = None

        self.model_type = None

        self.model_hyperparameters = {}

        self.last_metrics = None

        self.last_trained_at = None

    def is_dataset_loaded(self):

        if self.df is None:
            return False

        if self.df.empty:
            return False

        return True

    def save_churn_model(self):

        if self.model is None:
            raise ValueError(
                "Model is not trained"
            )

        joblib.dump(
            {
                "model": self.model,
                "model_type": self.model_type,
                "hyperparameters":
                    self.model_hyperparameters
            },
            "models/churn_model.joblib"
        )

    def get_preview(self, rows: int = 5):

        if not self.is_dataset_loaded():
            raise ValueError(
                "Dataset is not loaded or empty"
            )

        return self.df.head(rows)

    def load_churn_model(self):

        model_path = "models/churn_model.joblib"

        if not os.path.exists(model_path):
            return False

        saved_data = joblib.load(
            model_path
        )
        self.model = (
            saved_data["model"]
        )

        self.model_type = (
            saved_data["model_type"]
        )

        self.model_hyperparameters = (
            saved_data["hyperparameters"]
        )

        return True

    def get_info(self):
        if not self.is_dataset_loaded():
            raise ValueError(
                "Dataset is not loaded or empty"
            )
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "features": self.df.columns.tolist(),
            "churn_distribution": self.df["churn"].value_counts().to_dict()
        }

    def prepare_data(self):
        if not self.is_dataset_loaded():
            raise ValueError(
                "Dataset is not loaded or empty"
            )
        X = self.df.drop(columns=["churn"])

        y = self.df["churn"]

        X = X.fillna(0)

        return X, y

    def split_data(self):
        X, y = self.prepare_data()

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y
        )

        return (
            X_train,
            X_test,
            y_train,
            y_test
        )

    def get_split_info(self):
        X_train, X_test, y_train, y_test = self.split_data()

        return {
            "train_size": len(X_train),
            "test_size": len(X_test),

            "train_churn_distribution":
                y_train.value_counts().to_dict(),

            "test_churn_distribution":
                y_test.value_counts().to_dict()
        }

    def get_model_status(self):

        return {
            "is_trained":
                self.model is not None,

            "model_type":
                self.model_type,

            "hyperparameters":
                self.model_hyperparameters,

            "last_trained_at":
                self.last_trained_at,

            "metrics":
                self.last_metrics
        }

    def train_churn_model(
                self,
                config: TrainingConfigChurn
        ):

        if not self.is_dataset_loaded():
            raise ValueError(
                "Dataset is not loaded or empty"
            )
        X_train, X_test, y_train, y_test = self.split_data()

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    StandardScaler(),
                    self.numeric_features
                ),
                (
                    "cat",
                    OneHotEncoder(
                        handle_unknown="ignore"
                    ),
                    self.categorical_features
                )
            ]
        )
        if config.model_type == "logreg":

            classifier = LogisticRegression(
                **config.hyperparameters
            )

        elif config.model_type == "random_forest":

            classifier = RandomForestClassifier(
                **config.hyperparameters
            )

        else:

            raise ValueError(
                f"Unsupported model type: {config.model_type}"
            )

        pipeline = Pipeline(
            steps=[
                (
                    "preprocessor",
                    preprocessor
                ),
                (
                    "classifier",
                    classifier
                )
            ]
        )

        pipeline.fit(
            X_train,
            y_train
        )

        predictions = pipeline.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            predictions
        )

        f1 = f1_score(
            y_test,
            predictions
        )

        self.model = pipeline

        self.model_type = config.model_type

        self.model_hyperparameters = (
            config.hyperparameters
        )

        self.last_metrics = {
            "accuracy": round(
                float(accuracy),
                4
            ),
            "f1": round(
                float(f1),
                4
            )
        }

        self.last_trained_at = (
            datetime.now()
            .strftime("%Y-%m-%d %H:%M:%S")
        )

        self.save_churn_model()

        return self.last_metrics

    def predict_churn(self, features: dict):

        if self.model is None:
            raise ValueError(
                "Model is not trained"
            )

        input_df = pd.DataFrame(
            [features]
        )

        input_df = input_df[
            self.feature_columns
        ]

        prediction = self.model.predict(
            input_df
        )[0]

        probabilities = (
            self.model.predict_proba(
                input_df
            )[0]
        )

        return {
            "prediction": int(prediction),
            "probability_stay": float(probabilities[0]),
            "probability_churn": float(probabilities[1])
        }

    def get_model_schema(self):

        return {
            "features": {
                "monthly_fee": "float",
                "usage_hours": "float",
                "support_requests": "int",
                "account_age_months": "int",
                "failed_payments": "int",
                "region": "str",
                "device_type": "str",
                "payment_method": "str",
                "autopay_enabled": "int"
            }
        }

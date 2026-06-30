import pandas as pd

from sklearn.model_selection import train_test_split

from sklearn.compose import ColumnTransformer

from sklearn.pipeline import Pipeline

from sklearn.preprocessing import (
    StandardScaler,
    OneHotEncoder
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

    def is_dataset_loaded(self):

        if self.df is None:
            return False

        if self.df.empty:
            return False

        return True

    def get_preview(self, rows: int = 5):

        if not self.is_dataset_loaded():
            raise ValueError(
                "Dataset is not loaded or empty"
            )

        return self.df.head(rows)

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

    def train_churn_model(self):
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

        pipeline = Pipeline(
            steps=[
                (
                    "preprocessor",
                    preprocessor
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000
                    )
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

        return {
            "accuracy": round(
                float(accuracy),
                4
            ),
            "f1": round(
                float(f1),
                4
            )
        }


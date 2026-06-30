from __future__ import annotations

import pytest

from services.dataset_service import DatasetService

from models.schemas import (
    TrainingConfigChurn
)


def test_dataset_loaded():

    service = DatasetService()

    assert service.is_dataset_loaded() is True


def test_prepare_data():

    service = DatasetService()

    X, y = service.prepare_data()

    assert len(X) > 0

    assert len(y) > 0

    assert "churn" not in X.columns


def test_split_data():

    service = DatasetService()

    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = service.split_data()

    assert len(X_train) > 0

    assert len(X_test) > 0

    assert len(y_train) > 0

    assert len(y_test) > 0


def test_train_model():

    service = DatasetService()

    config = TrainingConfigChurn(
        model_type="logreg"
    )

    metrics = service.train_churn_model(
        config
    )

    assert "accuracy" in metrics

    assert "f1" in metrics

    assert isinstance(
        metrics["accuracy"],
        float
    )

    assert isinstance(
        metrics["f1"],
        float
    )

    assert service.model is not None


def test_predict_without_model():

    service = DatasetService()

    with pytest.raises(
        ValueError,
        match="Model is not trained"
    ):
        service.predict_churn({})
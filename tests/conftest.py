"""Shared fixtures. Nothing here touches the network, MongoDB, DagsHub or AWS."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from app.constants.training_pipeline import TARGET_COLUMN
from app.utils.main_utils.utils import read_yaml_file, save_object

SCHEMA_PATH = Path("data_schema/schema.yaml")


@pytest.fixture(scope="session")
def feature_columns() -> list[str]:
    """The 30 feature names, read from the real schema.yaml."""
    schema = read_yaml_file(SCHEMA_PATH)
    return [name for item in schema["columns"] for name in item if name != TARGET_COLUMN]


@pytest.fixture
def make_rows(feature_columns):
    """Factory: make_rows(n) -> list of n feature dicts with values in {-1, 0, 1}."""

    def _make(n: int = 3, seed: int = 0) -> list[dict]:
        rng = np.random.default_rng(seed)
        values = rng.choice([-1, 0, 1], size=(n, len(feature_columns)))
        return pd.DataFrame(values, columns=feature_columns).to_dict("records")

    return _make


@pytest.fixture
def tiny_model_dir(tmp_path, feature_columns) -> Path:
    """Train a tiny REAL imputer + decision tree and save them like the pipeline does."""
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        rng.choice([-1, 0, 1], size=(200, len(feature_columns))).astype(float),
        columns=feature_columns,
    )
    y = (X.iloc[:, 0] > 0).astype(int)  # label 1 (legitimate) when the first feature is 1

    preprocessor = Pipeline([("imputer", KNNImputer(n_neighbors=3))]).fit(X)
    model = DecisionTreeClassifier(random_state=0).fit(preprocessor.transform(X), y)

    model_dir = tmp_path / "final_models"
    save_object(model_dir / "preprocessor.pkl", preprocessor)
    save_object(model_dir / "model.pkl", model)
    return model_dir

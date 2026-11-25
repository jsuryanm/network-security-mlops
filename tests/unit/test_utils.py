import sys

import numpy as np
import pytest

from app.constants.training_pipeline import TARGET_COLUMN
from app.exception.exceptions import NetworkSecurityException
from app.utils.main_utils.utils import (
    load_numpy_array_data,
    load_object,
    read_yaml_file,
    save_numpy_array_data,
    save_object,
    write_yaml_file,
)
from app.utils.ml_utils.classification_metric import get_classification_score


def test_object_roundtrip(tmp_path):
    path = tmp_path / "nested" / "obj.pkl"  # parent folder is created for us
    save_object(path, {"a": 1})
    assert load_object(path) == {"a": 1}


def test_load_missing_object_raises_project_exception(tmp_path):
    with pytest.raises(NetworkSecurityException):
        load_object(tmp_path / "missing.pkl")


def test_numpy_roundtrip(tmp_path):
    array = np.arange(12).reshape(3, 4)
    save_numpy_array_data(tmp_path / "x" / "a.npy", array)
    np.testing.assert_array_equal(load_numpy_array_data(tmp_path / "x" / "a.npy"), array)


def test_yaml_roundtrip_and_no_replace(tmp_path):
    path = tmp_path / "c.yaml"
    write_yaml_file(path, {"k": 1})
    write_yaml_file(path, {"k": 2}, replace=False)  # must keep the first value
    assert read_yaml_file(path) == {"k": 1}


def test_real_schema_has_31_columns_including_target():
    schema = read_yaml_file("data_schema/schema.yaml")
    names = [name for item in schema["columns"] for name in item]
    assert len(names) == 31
    assert TARGET_COLUMN in names


def test_perfect_predictions_score_one():
    metric = get_classification_score([0, 1, 1, 0], [0, 1, 1, 0])
    assert metric.f1_score == metric.precision_score == metric.recall_score == 1.0


def test_exception_keeps_original_error_and_location():
    try:
        try:
            1 / 0
        except ZeroDivisionError as e:
            raise NetworkSecurityException(e, sys) from e
    except NetworkSecurityException as wrapped:
        assert isinstance(wrapped.error_message, ZeroDivisionError)
        assert "test_utils.py" in str(wrapped)
        assert wrapped.lineno > 0

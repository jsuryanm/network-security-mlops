import pytest
from pydantic import ValidationError

from app.api.schemas import PredictRequest, TrainingStatus


def test_valid_request(make_rows):
    assert len(PredictRequest(records=make_rows(2)).records) == 2


def test_empty_records_rejected():
    with pytest.raises(ValidationError):
        PredictRequest(records=[])


def test_too_many_records_rejected(make_rows):
    with pytest.raises(ValidationError):
        PredictRequest(records=make_rows(1001))


def test_non_integer_value_rejected(make_rows):
    row = make_rows(1)[0]
    row[next(iter(row))] = "abc"
    with pytest.raises(ValidationError):
        PredictRequest(records=[row])


def test_swagger_example_matches_schema_columns(feature_columns):
    """The prefilled /docs example must stay valid when schema.yaml changes."""
    example = PredictRequest.model_json_schema()["example"]
    assert len(example["records"]) == 2
    for record in example["records"]:
        assert set(record) == set(feature_columns)
        assert set(record.values()) <= {-1, 0, 1}
    PredictRequest(**example)  # and it parses


def test_training_status_defaults_to_idle():
    status = TrainingStatus()
    assert status.status == "idle"
    assert status.error is None and status.test_f1_score is None


def test_training_status_rejects_unknown_state():
    with pytest.raises(ValidationError):
        TrainingStatus(status="paused")

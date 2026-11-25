import numpy as np
import pandas as pd
import pytest

from app.pipeline.batch_pipeline import predict_frame


class StubModel:
    """Predicts 1 when the first feature is positive. Counts how often it is called."""

    def __init__(self):
        self.calls = 0

    def predict(self, X):
        self.calls += 1
        return (X.iloc[:, 0] > 0).astype(int).to_numpy()


@pytest.fixture
def frame(feature_columns, make_rows):
    return pd.DataFrame(make_rows(10))[feature_columns]


def test_adds_prediction_and_label_columns(frame, feature_columns):
    out = predict_frame(StubModel(), frame, feature_columns)
    assert list(out.columns[-2:]) == ["prediction", "label"]
    assert len(out) == len(frame)
    assert set(out["label"]) <= {"phishing", "legitimate"}


def test_label_matches_prediction(frame, feature_columns):
    out = predict_frame(StubModel(), frame, feature_columns)
    assert (out.loc[out.prediction == 1, "label"] == "legitimate").all()
    assert (out.loc[out.prediction == 0, "label"] == "phishing").all()


def test_chunking_keeps_row_order(frame, feature_columns):
    model = StubModel()
    chunked = predict_frame(model, frame, feature_columns, chunk_size=3)
    whole = predict_frame(StubModel(), frame, feature_columns, chunk_size=1000)
    assert model.calls == 4  # 10 rows in chunks of 3 -> 3 + 3 + 3 + 1
    pd.testing.assert_frame_equal(chunked, whole)


def test_target_column_is_ignored(frame, feature_columns):
    with_target = frame.assign(Result=1)
    out = predict_frame(StubModel(), with_target, feature_columns)
    assert "Result" not in out.columns


def test_missing_feature_raises(frame, feature_columns):
    with pytest.raises(ValueError, match="feature mismatch"):
        predict_frame(StubModel(), frame.drop(columns=[feature_columns[0]]), feature_columns)


def test_extra_feature_raises(frame, feature_columns):
    with pytest.raises(ValueError, match="feature mismatch"):
        predict_frame(StubModel(), frame.assign(unexpected=1), feature_columns)


def test_missing_values_raise(frame, feature_columns):
    frame = frame.astype(float)
    frame.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="missing values"):
        predict_frame(StubModel(), frame, feature_columns)


def test_empty_frame_returns_empty_result(feature_columns):
    empty = pd.DataFrame(columns=feature_columns)
    out = predict_frame(StubModel(), empty, feature_columns)
    assert len(out) == 0

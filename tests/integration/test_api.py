import io
from types import SimpleNamespace

import pandas as pd
import pytest

import app.api.routes.batch as batch_route
import app.api.routes.health as health_route
import app.api.routes.train as train_route
from app.api.schemas import TrainingStatus

pytestmark = pytest.mark.integration


def to_csv(rows) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode()


# ---------- health ----------

def test_health_ok(client, monkeypatch):
    async def mlflow_ok(_request):
        return True

    monkeypatch.setattr(health_route, "_ping_mlflow", mlflow_ok)
    body = client.get("/health").json()
    assert body == {"status": "ok", "model_loaded": True, "mongodb": True, "mlflow": True}


def test_health_degraded_without_model(no_model_client, monkeypatch):
    async def mlflow_ok(_request):
        return True

    monkeypatch.setattr(health_route, "_ping_mlflow", mlflow_ok)
    body = no_model_client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["model_loaded"] is False


def test_health_reports_mongo_down(client, monkeypatch):
    async def mlflow_ok(_request):
        return True

    monkeypatch.setattr(health_route, "_ping_mlflow", mlflow_ok)
    client.app.state.mongo.ping_works = False
    body = client.get("/health").json()
    assert body["mongodb"] is False and body["status"] == "degraded"


# ---------- predict ----------

def test_predict_returns_labels_and_logs_rows(client, make_rows):
    rows = make_rows(3)
    response = client.post("/predict", json={"records": rows})
    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert len(predictions) == 3
    for item in predictions:
        assert item["label"] == ("legitimate" if item["prediction"] == 1 else "phishing")

    logged = client.app.state.predictions.docs  # the background task ran
    assert len(logged) == 3
    assert [d["prediction"] for d in logged] == [p["prediction"] for p in predictions]
    assert logged[0]["features"] == rows[0]


def test_predict_matches_the_model_directly(client, make_rows):
    rows = make_rows(5, seed=7)
    body = client.post("/predict", json={"records": rows}).json()
    api = [p["prediction"] for p in body["predictions"]]
    frame = pd.DataFrame(rows)[client.app.state.feature_columns]
    assert api == [int(x) for x in client.app.state.model.predict(frame)]


def test_predict_rejects_missing_feature(client, make_rows):
    row = make_rows(1)[0]
    missing = next(iter(row))
    del row[missing]
    response = client.post("/predict", json={"records": [row]})
    assert response.status_code == 422
    assert missing in response.json()["detail"]


def test_predict_rejects_extra_feature(client, make_rows):
    row = {**make_rows(1)[0], "bonus": 1}
    assert client.post("/predict", json={"records": [row]}).status_code == 422


def test_predict_rejects_bad_payloads(client):
    assert client.post("/predict", json={"records": []}).status_code == 422
    assert client.post("/predict", json={}).status_code == 422


def test_predict_503_without_model(no_model_client, make_rows):
    response = no_model_client.post("/predict", json={"records": make_rows(1)})
    assert response.status_code == 503


# ---------- history ----------

def test_predictions_history_pages(client, make_rows):
    client.post("/predict", json={"records": make_rows(2)})
    client.post("/predict", json={"records": make_rows(2, seed=1)})
    page = client.get("/predictions", params={"limit": 3}).json()
    assert page["total"] == 4
    assert len(page["items"]) == 3
    assert client.get("/predictions", params={"limit": 0}).status_code == 422


# ---------- batch ----------

def test_batch_predict_returns_csv(client, make_rows):
    rows = make_rows(25)
    response = client.post(
        "/batch/predict", files={"file": ("rows.csv", to_csv(rows), "text/csv")}
    )
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    out = pd.read_csv(io.BytesIO(response.content))
    assert len(out) == 25
    assert list(out.columns[-2:]) == ["prediction", "label"]


def test_batch_rejects_non_csv(client):
    response = client.post("/batch/predict", files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == 415


def test_batch_rejects_missing_column(client, make_rows):
    rows = pd.DataFrame(make_rows(3)).drop(columns=["port"]).to_dict("records")
    response = client.post("/batch/predict", files={"file": ("r.csv", to_csv(rows), "text/csv")})
    assert response.status_code == 422
    assert "port" in response.json()["detail"]


def test_batch_rejects_empty_file(client):
    response = client.post("/batch/predict", files={"file": ("e.csv", b"", "text/csv")})
    assert response.status_code == 422


def test_batch_rejects_oversized_file(client, make_rows, monkeypatch):
    monkeypatch.setattr(batch_route, "MAX_UPLOAD_BYTES", 10)
    response = client.post(
        "/batch/predict", files={"file": ("r.csv", to_csv(make_rows(3)), "text/csv")}
    )
    assert response.status_code == 413


def test_batch_503_without_model(no_model_client, make_rows):
    response = no_model_client.post(
        "/batch/predict", files={"file": ("r.csv", to_csv(make_rows(1)), "text/csv")}
    )
    assert response.status_code == 503


# ---------- training (the slow pipeline is replaced by a stub) ----------

def test_train_success_updates_status(client, monkeypatch):
    artifact = SimpleNamespace(test_metric_artifact=SimpleNamespace(f1_score=0.95))
    monkeypatch.setattr(train_route, "_train_blocking", lambda: artifact)

    assert client.post("/train").status_code == 202
    status = client.get("/train/status").json()
    assert status["status"] == "succeeded"
    assert status["test_f1_score"] == 0.95
    assert status["finished_at"] is not None


def test_train_failure_is_reported(client, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(train_route, "_train_blocking", boom)
    client.post("/train")
    status = client.get("/train/status").json()
    assert status["status"] == "failed"
    assert "boom" in status["error"]


def test_train_409_when_already_running(client):
    client.app.state.training = TrainingStatus(status="running")
    assert client.post("/train").status_code == 409


# ---------- model reload ----------

def test_model_hot_reload_after_files_appear(
    no_model_client, tiny_model_dir, monkeypatch, make_rows
):
    import app.api.deps as deps

    assert no_model_client.post("/predict", json={"records": make_rows(1)}).status_code == 503
    monkeypatch.setattr(deps, "FINAL_MODEL_DIR", tiny_model_dir)  # "training finished"

    import anyio

    anyio.run(deps.reload_model, no_model_client.app)
    assert no_model_client.post("/predict", json={"records": make_rows(1)}).status_code == 200

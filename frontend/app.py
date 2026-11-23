"""Simple Streamlit UI for the phishing detector API.

Run the API first:  uv run uvicorn app.api.main:app
Then:               uv run streamlit run frontend/app.py
"""
import os
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
import yaml

API_URL = os.getenv("API_URL", "http://localhost:8000")
SCHEMA = Path(__file__).resolve().parent.parent / "data_schema" / "schema.yaml"

# Dataset encoding for each feature: -1, 0 or 1 (meaning differs per feature).
FEATURES = [name for item in yaml.safe_load(SCHEMA.read_text())["columns"] for name in item if name != "Result"]

st.set_page_config(page_title="Phishing Detector", page_icon="🎣", layout="wide")
st.title("Phishing Website Detector")


def call(method: str, path: str, **kwargs):
    """Call the API. Show the error in the UI and return None on failure."""
    try:
        r = httpx.request(method, f"{API_URL}{path}", timeout=60, **kwargs)
        r.raise_for_status()
        return r
    except httpx.HTTPStatusError as e:
        st.error(f"API {e.response.status_code}: {e.response.text}")
    except httpx.HTTPError as e:
        st.error(f"Cannot reach API at {API_URL}: {e}")
    return None


with st.sidebar:
    st.subheader("API status")
    r = call("GET", "/health")
    if r:
        h = r.json()
        st.write(f"Model loaded: {'✅' if h['model_loaded'] else '❌'}")
        st.write(f"MongoDB: {'✅' if h['mongodb'] else '❌'}")
        st.write(f"MLflow: {'✅' if h['mlflow'] else '❌'}")
    st.button("Refresh")

single, batch, history, train = st.tabs(["Single check", "Batch CSV", "History", "Train"])

with single:
    st.caption("Set each feature to -1, 0 or 1 (as in the dataset), then predict.")
    cols = st.columns(5)
    record = {
        name: cols[i % 5].selectbox(name, [-1, 0, 1], index=2, key=f"f_{name}")
        for i, name in enumerate(FEATURES)
    }
    if st.button("Predict", type="primary"):
        r = call("POST", "/predict", json={"records": [record]})
        if r:
            p = r.json()["predictions"][0]
            (st.success if p["label"] == "legitimate" else st.error)(f"Result: **{p['label']}**")

with batch:
    up = st.file_uploader("CSV with the 30 feature columns (a `Result` column is ignored)", type="csv")
    if up and st.button("Run batch prediction"):
        r = call("POST", "/batch/predict", files={"file": (up.name, up.getvalue(), "text/csv")})
        if r:
            from io import BytesIO

            out = pd.read_csv(BytesIO(r.content))
            st.write(out["label"].value_counts())
            st.dataframe(out, width="stretch")
            st.download_button("Download predictions.csv", r.content, "predictions.csv", "text/csv")

with history:
    limit = st.slider("Rows", 5, 100, 20)
    r = call("GET", "/predictions", params={"limit": limit})
    if r:
        data = r.json()
        st.caption(f"{data['total']} predictions logged")
        if data["items"]:
            df = pd.DataFrame(data["items"])
            df["features"] = df["features"].astype(str)
            st.dataframe(df, width="stretch")

with train:
    st.caption("Runs the full pipeline (ingestion to model). Takes a while.")
    if st.button("Start training"):
        call("POST", "/train")
    r = call("GET", "/train/status")
    if r:
        st.json(r.json())

# How the FastAPI backend works

A beginner-friendly tour of [app/api/](../app/api/). Read top to bottom, about 10 minutes.

## 1. The big picture

FastAPI turns Python functions into web endpoints. A client (the Streamlit UI, `curl`, a browser) sends an HTTP request. FastAPI calls the matching function and sends back JSON.

```mermaid
flowchart LR
    UI[Streamlit UI<br/>frontend/app.py] -->|HTTP JSON| API
    CURL[curl / Swagger<br/>/docs] -->|HTTP JSON| API
    subgraph API[FastAPI app]
        R[routes/<br/>endpoints] --> M[(model in memory)]
        R --> P[batch_pipeline.py<br/>chunked scoring]
        R --> T[training_pipeline.py]
    end
    R <-->|async| DB[(MongoDB<br/>predictions)]
    R -->|ping| ML[MLflow / DagsHub]
    M -.loaded from.-> F[final_models/<br/>model.pkl + preprocessor.pkl]
    T -.writes.-> F
```

## 2. File map

| File | Job |
|---|---|
| [main.py](../app/api/main.py) | Creates the `app`, runs startup/shutdown code (the "lifespan"), plugs in the routes |
| [schemas.py](../app/api/schemas.py) | Pydantic models: the exact shape of every request and response |
| [deps.py](../app/api/deps.py) | Shared helpers: load the model, current time |
| [routes/health.py](../app/api/routes/health.py) | `GET /health` |
| [routes/predict.py](../app/api/routes/predict.py) | `POST /predict` |
| [routes/predictions.py](../app/api/routes/predictions.py) | `GET /predictions` (history) |
| [routes/batch.py](../app/api/routes/batch.py) | `POST /batch/predict` (CSV in, CSV out) |
| [routes/train.py](../app/api/routes/train.py) | `POST /train`, `GET /train/status` |
| [pipeline/batch_pipeline.py](../app/pipeline/batch_pipeline.py) | Scoring logic for batches, no FastAPI inside |

Why one file per endpoint group? Each file stays short, and `routes/__init__.py` joins them into one `api_router`.

## 3. Startup: the lifespan

Heavy things are created **once** when the server starts, not on every request. That lives in `lifespan` in `main.py`:

```mermaid
sequenceDiagram
    participant S as uvicorn
    participant L as lifespan()
    participant A as app.state
    S->>L: server starting
    L->>A: Mongo client (AsyncMongoClient)
    L->>A: feature column names (from schema.yaml)
    L->>A: model (load .pkl files in a thread)
    L->>A: training status = idle
    Note over S,A: server now accepts requests
    S->>L: server stopping
    L->>A: close Mongo client
```

`app.state` is just a shared notebook. Endpoints reach it through `request.app.state.model`, `request.app.state.predictions`, and so on.

If `final_models/` is empty, the API still starts. `/predict` answers `503` until you train.

## 4. What "async" means here

- `async def` endpoints run on one event loop. While one request waits (database, network), the loop serves others.
- `await` marks the waiting point.
- Sklearn and pandas are **blocking** (they hog the CPU). Calling them directly would freeze every other request. So we wrap them: `await asyncio.to_thread(model.predict, frame)`. It runs in a worker thread and the loop stays free.
- `asyncio.gather(a(), b())` starts two waits at the same time. Total time is the slowest one, not the sum.

Where it is used:

| Place | What runs in parallel |
|---|---|
| `GET /health` | MongoDB ping + MLflow ping |
| `GET /predictions` | `count_documents` + the page of rows |
| `POST /batch/predict` | Chunks of 10,000 rows scored in a thread pool |
| `POST /predict` | Mongo logging runs *after* the response (BackgroundTasks) |

## 5. Request walkthrough: `POST /predict`

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant T as Thread
    participant DB as MongoDB
    C->>F: {"records":[{30 features}]}
    F->>F: Pydantic checks types (bad = 422)
    F->>F: feature names match schema? (bad = 422)
    F->>T: model.predict(frame)
    T-->>F: [0, 1, ...]
    F-->>C: 200 {"predictions":[{"prediction":0,"label":"phishing"}]}
    F->>DB: insert_many (background, after reply)
```

Example request body. Every record needs all 30 features, each `-1`, `0` or `1`. This is a real row from the dataset (a phishing site), and the second is a legitimate one:

```json
{
  "records": [
    {"having_IP_Address": -1, "URL_Length": 1, "Shortining_Service": 1, "having_At_Symbol": 1, "double_slash_redirecting": -1, "Prefix_Suffix": -1, "having_Sub_Domain": -1, "SSLfinal_State": -1, "Domain_registeration_length": -1, "Favicon": 1, "port": 1, "HTTPS_token": -1, "Request_URL": 1, "URL_of_Anchor": -1, "Links_in_tags": 1, "SFH": -1, "Submitting_to_email": -1, "Abnormal_URL": -1, "Redirect": 0, "on_mouseover": 1, "RightClick": 1, "popUpWidnow": 1, "Iframe": 1, "age_of_domain": -1, "DNSRecord": -1, "web_traffic": -1, "Page_Rank": -1, "Google_Index": 1, "Links_pointing_to_page": 1, "Statistical_report": -1},
    {"having_IP_Address": 1, "URL_Length": 0, "Shortining_Service": -1, "having_At_Symbol": 1, "double_slash_redirecting": 1, "Prefix_Suffix": -1, "having_Sub_Domain": 1, "SSLfinal_State": 1, "Domain_registeration_length": -1, "Favicon": 1, "port": 1, "HTTPS_token": 1, "Request_URL": 1, "URL_of_Anchor": 0, "Links_in_tags": 0, "SFH": -1, "Submitting_to_email": 1, "Abnormal_URL": 1, "Redirect": 0, "on_mouseover": -1, "RightClick": 1, "popUpWidnow": -1, "Iframe": 1, "age_of_domain": -1, "DNSRecord": -1, "web_traffic": 0, "Page_Rank": -1, "Google_Index": 1, "Links_pointing_to_page": 1, "Statistical_report": 1}
  ]
}
```

Response:

```json
{"predictions": [{"prediction": 0, "label": "phishing"}, {"prediction": 1, "label": "legitimate"}]}
```

The same example is prefilled in Swagger (`/docs`, "Try it out"), so you can click Execute straight away.

Key ideas in `routes/predict.py`:
- `body: PredictRequest` makes FastAPI parse and validate the JSON for you. No manual parsing.
- `response_model=PredictResponse` makes FastAPI check and shape what you return.
- `HTTPException(503, ...)` becomes a proper HTTP error with a message.
- `background.add_task(...)` runs after the reply, so the user does not wait for Mongo. If the insert fails it is logged, not raised.

Label meaning: `1` = legitimate, `0` = phishing. (Transformation maps the dataset's `-1` to `0`.)

## 6. Batch: `POST /batch/predict`

```mermaid
flowchart TD
    A[Upload .csv] --> B{.csv and under 20 MB?}
    B -- no --> X1[415 / 413]
    B -- yes --> C[pandas.read_csv in thread]
    C --> D{columns match, no NaN?}
    D -- no --> X2[422 with the diff]
    D -- yes --> E[split into 10k-row chunks]
    E --> F1[chunk 1 predict]
    E --> F2[chunk 2 predict]
    E --> F3[chunk N predict]
    F1 & F2 & F3 --> G[join in original order]
    G --> H[add prediction + label columns]
    H --> I[stream predictions.csv back]
```

`predict_frame()` in `batch_pipeline.py` is a plain function with no FastAPI in it. That makes it easy to test alone.

## 7. Training: `POST /train`

Training takes minutes, so the endpoint does not wait for it.

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant B as Background task
    participant P as TrainingPipeline
    C->>F: POST /train
    alt already running
        F-->>C: 409
    else idle
        F-->>C: 202 status=running
        F->>B: start
        B->>P: run in thread (ingest, validate, transform, train)
        P-->>B: artifact (F1 score, files)
        B->>F: reload model into memory
        B->>F: status = succeeded / failed
    end
    C->>F: GET /train/status
    F-->>C: running / succeeded / failed
```

After success the new model is hot-swapped. No server restart needed.

Limits to know: status lives in memory, so run **one** uvicorn worker. The trainer imports DagsHub when it loads, so the pipeline is imported lazily inside the thread. That way the API starts even if DagsHub is down.

## 8. Error codes you will see

| Code | Meaning |
|---|---|
| 200 | OK |
| 202 | Training accepted, running in background |
| 409 | Training already running |
| 413 | Upload larger than 20 MB |
| 415 | Upload is not a `.csv` |
| 422 | Bad input: wrong types, wrong or missing features, bad CSV |
| 503 | No model loaded yet, or MongoDB down |

## 9. Try it

```bash
uv run uvicorn app.api.main:app --reload     # API on http://localhost:8000
# open http://localhost:8000/docs            # interactive Swagger page, click "Try it out"
uv run streamlit run frontend/app.py         # UI on http://localhost:8501
```

`curl` example:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/batch/predict -F "file=@data/phisingData.csv" -o out.csv
```

## 10. Where to read the code first

1. [schemas.py](../app/api/schemas.py): small, shows what goes in and out.
2. [routes/predict.py](../app/api/routes/predict.py): the core flow.
3. [main.py](../app/api/main.py): how startup wires things.
4. [routes/train.py](../app/api/routes/train.py): background work.

## 11. In what order to write the files

Build from the bottom up: write things that depend on nothing first, and test after every step. Each step ends with something you can run.

```mermaid
flowchart TD
    S1[1. schemas.py] --> S2[2. deps.py]
    S2 --> S3[3. routes/health.py + main.py]
    S3 --> S4[4. routes/predict.py]
    S4 --> S5[5. routes/predictions.py]
    S5 --> S6[6. pipeline/batch_pipeline.py]
    S6 --> S7[7. routes/batch.py]
    S7 --> S8[8. routes/train.py]
    S8 --> S9[9. routes/__init__.py cleanup]
    S9 --> S10[10. frontend/app.py]
```

| # | File | Write this | Check it works |
|---|---|---|---|
| 1 | `schemas.py` | Pydantic request/response models. No imports from the rest of the app, so nothing can break | `python -c "from app.api.schemas import PredictRequest"` |
| 2 | `deps.py` | `now()`, model loader, `reload_model()`. Plain Python, no endpoints yet | Call `_load_network_model()` in a shell, it returns a model |
| 3 | `routes/health.py` + `main.py` | The smallest endpoint, plus the lifespan that creates Mongo client and loads the model. This proves the wiring | `uvicorn app.api.main:app`, open `/health` and `/docs` |
| 4 | `routes/predict.py` | The core feature: validate, `to_thread` predict, background log | Swagger "Try it out" with the example body |
| 5 | `routes/predictions.py` | Reads back what step 4 logged. Uses `asyncio.gather` | `/predictions` shows your rows |
| 6 | `pipeline/batch_pipeline.py` | `predict_frame()` as a pure function, no FastAPI | Run it on `data/phisingData.csv` in a shell, try `chunk_size=7` |
| 7 | `routes/batch.py` | Thin wrapper: upload, call step 6, return CSV | Upload a CSV in Swagger |
| 8 | `routes/train.py` | Background task. Last because it is slowest to test and needs everything else | `POST /train`, poll `/train/status` |
| 9 | `routes/__init__.py` | Split into modules once they work. Until now you can register each router straight in `main.py` | All paths appear in `/docs` |
| 10 | `frontend/app.py` | A UI only makes sense once the API is stable | `streamlit run frontend/app.py` |

Rules of thumb:
- **Schemas first.** Deciding the input/output shape up front tells you what every endpoint must do.
- **Smallest endpoint first.** `/health` tells you early if the lifespan, settings or Mongo are broken, before any logic is involved.
- **Logic in plain functions, endpoints stay thin.** Step 6 before step 7 means you can test the hard part without HTTP.
- **Slow or risky features last.** Training is minutes long and touches DagsHub, so add it once the rest is solid.
- **Run the app after every step.** A bug found one file after you wrote it is easy to place.

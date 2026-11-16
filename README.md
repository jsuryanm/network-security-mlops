# network-security-mlops
End-to-end MLOps project that detects **phishing websites** from 30 URL/page features (each `-1`, `0` or `1`).

## Project status

| Stage | Status | Where |
|---|---|---|
| Push data to MongoDB | Done | [push_data.py](push_data.py) |
| Data ingestion (MongoDB to train/test CSV) | Done | [app/components/data_ingestion.py](app/components/data_ingestion.py) |
| Data validation (schema check + data drift) | Done | [app/components/data_validation.py](app/components/data_validation.py) |
| Data transformation, model training, API | Not started | |
| Experiments (EDA, features, models) | Done | [notebooks/](notebooks/) |

Best model so far (notebooks): HistGradientBoosting, test F1 0.974 (recall 96.6%, precision 98.2%).

## Project layout
```
app/components/   pipeline stages (ingestion, validation)
app/entity/       config and artifact schemas
app/constants/    constants (paths, drift thresholds)
app/utils/        shared helpers (YAML read/write)
data_schema/      schema.yaml, the expected columns
notebooks/        experiments only, no production code
docs/             guides
```

## Prerequisites
- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)
- A MongoDB instance (MongoDB Atlas free tier or a local `mongod`)

## Install
```bash
uv sync
```

## MongoDB setup

### Option A: MongoDB Atlas (cloud)
1. Create a free cluster at https://cloud.mongodb.com.
2. **Database Access**: add a database user (username + password).
3. **Network Access**: add your IP (or `0.0.0.0/0` for dev only).
4. **Connect, Drivers**: copy the connection string:
   ```
   mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   ```
   URL-encode special characters in the password (`@` becomes `%40`, etc.).

### Option B: Local MongoDB
```bash
docker run -d --name mongo -p 27017:27017 mongo:7
# URI: mongodb://localhost:27017
```

### Configure `.env`
```bash
cp .env.example .env
```
Fill in the MongoDB values. The app reads them in [app/core/config.py](app/core/config.py) via pydantic-settings:

```env
MONGODB_USERNAME=<user>
MONGODB_PASSWORD=<password>
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```
`MONGODB_URI` is the one used to connect. Never commit `.env`.

### Verify connection
```bash
uv run python -c "import pymongo, certifi; from app.core.config import get_settings; print(pymongo.MongoClient(get_settings().mongodb_uri, tlsCAFile=certifi.where()).admin.command('ping'))"
```
Expect `{'ok': 1.0}`.

## Push data to MongoDB
[push_data.py](push_data.py) reads the CSV, converts rows to JSON documents, and inserts them with `insert_many`.

1. Put the dataset at `data/phisingData.csv` (already in repo).
2. Optionally edit target names at the bottom of `push_data.py`:
   ```python
   file_path = 'data/phisingData.csv'
   database = "Surya"
   collection = "NetworkData"
   ```
3. Run from project root:
   ```bash
   uv run python push_data.py
   ```
   Prints the number of records inserted. Logs go to `logs/<YYYY-MM-DD>/<HH-MM-SS>.log`.

Check the data in Atlas (Browse Collections) or `mongosh`:
```bash
mongosh "$MONGODB_URI" --eval 'db.getSiblingDB("Surya").NetworkData.countDocuments()'
```

> Running the script twice inserts duplicates. Drop the collection first if you want a clean reload.

## Pipeline stages

Run from the project root. Each run writes to `Artifacts/<timestamp>/` (gitignored).

### 1. Data ingestion
Reads the MongoDB collection, saves a feature store CSV, and splits it 80/20 into `train.csv` and `test.csv`.
```bash
uv run python app/components/data_ingestion.py
```

### 2. Data validation
1. **Schema check:** train and test must have the columns listed in `data_schema/schema.yaml`.
2. **Data drift check** with [Evidently](https://github.com/evidentlyai/evidently): train is the reference, test is the current data.
   - A column drifts when its Jensen-Shannon distance is >= `0.1`.
   - The data counts as drifted if >= 30% of columns drift, **or** if `SSLfinal_State` or `URL_of_Anchor` drifts (the model relies on these two).
3. Files go to `validated/` when both checks pass, otherwise to `invalid/`.

Output in `Artifacts/<timestamp>/data_validation/`: `drift_report/report.yaml` (per-column distances) and `drift_report/report.html` (visual report).
Thresholds are constants in [app/constants/training_pipeline/__init__.py](app/constants/training_pipeline/__init__.py).

> Evidently does not import with pandas 3, so `pyproject.toml` pins `pandas<3`.

## Notebooks
Run in order. They read and write `Artifacts/notebooks/`.

| Notebook | What it does |
|---|---|
| [01_data_ingestion](notebooks/01_data_ingestion.ipynb) | Load (MongoDB or CSV), check, split |
| [02_eda](notebooks/02_eda.ipynb) | Data quality, target balance, feature vs target |
| [03_feature_engineering](notebooks/03_feature_engineering.ipynb) | Feature ranking, encoding, new features, PCA |
| [04_model_training_tuning](notebooks/04_model_training_tuning.ipynb) | Compare 10 models, tune with `RandomizedSearchCV` |
| [05_model_testing_evaluation](notebooks/05_model_testing_evaluation.ipynb) | Test-set metrics, thresholds, error analysis |

```bash
uv run jupyter lab notebooks/
```

## Docs
- [Logger guide](docs/logger.md)
- [Data drift with Evidently](docs/data_drift_evidently.md)
- [Data ingestion errors explained](docs/data_ingestion_errors.md)

# network-security-mlops
End-to-End Network Security MLOps Project

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

## Run
```bash
uv run python main.py
```

## Docs
- [Logger guide](docs/logger.md)

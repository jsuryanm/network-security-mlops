# Data Ingestion Errors: Why They Happened and How to Fix Them

Run command: `python app/components/data_ingestion.py`

## 1. The traceback

Three tracebacks are chained. Read them bottom to top. Only the first one is the real error.

| Order | Location | What it is |
|---|---|---|
| Root cause | `data_ingestion.py:34` | `AttributeError: database_name` |
| Wrapper 1 | `data_ingestion.py:49` | `export_collection_as_frame` catches it and re-raises `NetworkSecurityException` |
| Wrapper 2 | `data_ingestion.py:66` | `initiate_data_ingestion` catches it and re-raises `NetworkSecurityException` again |

The `except Exception as e: raise NetworkSecurityException(e, sys)` pattern wraps the same error twice. That is why the output looks long, and why the last line only says "line number [54]". It does not name the real cause.

## 2. Root cause: a class was passed where an instance was needed

Line 120:

```python
DataIngestion(DataIngestionConfig).initiate_data_ingestion()
```

`DataIngestionConfig` has no parentheses, so you passed the class itself. You did not pass an object created from it.

### Why this raises `AttributeError`

`DataIngestionConfig` is a pydantic `BaseModel`. Pydantic does not keep field defaults as ordinary class attributes.

- `database_name: str = training_pipeline.DATA_INGESTION_DATABASE_NAME` is stored in `DataIngestionConfig.model_fields`.
- It is not stored as `DataIngestionConfig.database_name`.
- Pydantic copies the default into the object's `__dict__` only when you create an instance.

So `self.data_ingestion_config.database_name` on a class goes to pydantic's metaclass `__getattr__`. That is the `_model_construction.py ... raise AttributeError(item)` line in the traceback.

The same problem would hit every property: `feature_store_file_path`, `training_file_path`, `testing_file_path`. On the class they are `property` objects, not paths.

### Fix

Create an instance:

```python
if __name__ == "__main__":
    config = DataIngestionConfig()
    artifact = DataIngestion(config).initiate_data_ingestion()
    logger.info(artifact)
```

## 3. Second error waiting behind the first

After fix 2, the run will probably fail in `initiate_data_ingestion`:

```python
DataIngestionArtifact(
    trained_file_path=self.data_ingestion_config.training_file_path,   # Path
    test_file_path=self.data_ingestion_config.testing_file_path,       # Path
)
```

`artifact_entity.py` declares both fields as `str`, but the config properties return `Path`. Pydantic v2 does not turn a `Path` into a `str`. It raises `ValidationError: Input should be a valid string`.

I did not run this, so treat it as a prediction from the code. It is a sound one, because pydantic v2 is strict about this case.

### Fix (pick one)

Option A, recommended: make the artifact use `Path`, which matches the config.

```python
from pathlib import Path
from pydantic import BaseModel


class DataIngestionArtifact(BaseModel):
    trained_file_path: Path
    test_file_path: Path
```

Option B: convert when you build it: `trained_file_path=str(self.data_ingestion_config.training_file_path)`.

## 4. Other bugs found in the same file

| Line | Problem | Fix |
|---|---|---|
| 45 | `df.replace({'na': np.nan})` returns a new frame and the result is thrown away, so nothing is replaced | `df = df.replace({'na': np.nan})` |
| 121 | `print(...)` breaks the project rule "never `print()`" | `logger.info(...)` |
| 37 | `MongoClient` is opened and never closed | `self.mongo_client.close()` in a `finally`, or use `with pymongo.MongoClient(...) as client:` |
| 29, 49, 66, 85, 117 | The try/except wraps the same error repeatedly, and `logger.exception(...)` is never called | Log once where the error happens with `logger.exception(...)`, then raise. Re-raise with `raise ... from e` to keep the cause. |
| 26-29 | The `try/except` around `self.x = y` can never fail | Remove it |
| 31, 87 | Public methods are missing return type hints | Add `-> pd.DataFrame` and `-> None` |

### Better exception wrapping

```python
except Exception as e:
    logger.exception("Failed to export collection as dataframe")
    raise NetworkSecurityException(e, sys) from e
```

If `NetworkSecurityException` already receives the underlying error, avoid wrapping it again higher up. For example, let `initiate_data_ingestion` re-raise `NetworkSecurityException` as it is:

```python
except NetworkSecurityException:
    raise
except Exception as e:
    raise NetworkSecurityException(e, sys) from e
```

## 5. Checklist

- [ ] `DataIngestion(DataIngestionConfig())` — add the parentheses
- [ ] `DataIngestionArtifact` fields changed to `Path`
- [ ] `df = df.replace(...)` assigns the result
- [ ] `print` replaced with `logger`
- [ ] `MongoClient` closed
- [ ] Re-run: `uv run python app/components/data_ingestion.py`

## 6. Lesson

For pydantic models, `Model` is the blueprint and `Model()` is the object. Config values such as defaults, validators and properties only work on the object. If you see `AttributeError: <field_name>` from `pydantic/_internal/_model_construction.py`, check first whether you passed the class instead of an instance.

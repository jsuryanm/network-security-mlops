# Detecting Data Drift with Evidently AI

How to detect data drift in this project (phishing-website classifier) using the open-source [Evidently](https://github.com/evidentlyai/evidently) library.

> The code below was run against Evidently **0.7.23** with the project's `train.csv` and `test.csv`. The outputs quoted in section 6 are real. See section 2 for a dependency conflict you must resolve first.

---

## 1. What is data drift, and why care?

A model learns patterns from **training data**. In production it sees **new data**. If the new data looks different, accuracy can fall without any error being raised.

| Term | Meaning | Example here |
|---|---|---|
| **Data drift** (covariate shift) | The distribution of the **inputs** changes | Attackers stop using IP addresses in URLs, so `having_IP_Address` shifts |
| **Target drift** | The distribution of the **label** changes | Phishing share rises from 44% to 70% |
| **Concept drift** | The **relationship** between inputs and label changes | An HTTPS certificate used to signal "safe" and no longer does |

Evidently's data drift report covers the first two directly, by comparing columns. It cannot see concept drift without labels. For that you need to compare model performance once true labels arrive.

**Why it matters for this project:** the model relies almost entirely on two features, `SSLfinal_State` and `URL_of_Anchor` (see notebook 05). If the way either feature is computed changes, the model can degrade badly while everything else looks fine.

---

## 2. Install

```bash
uv add evidently
```

> **Known conflict (I hit it):** `pyproject.toml` requires `pandas>=3.1.1`. With pandas 3.x in this project's venv, `import evidently` failed with
> `ImportError: cannot import name 'infer_dtype_from_object' from 'pandas.core.dtypes.common'`.
> Evidently 0.7.23 worked in a separate environment with **pandas 2.3.3**.
>
> I did not test other Evidently versions against pandas 3. Before adopting this, try `uv add evidently`, then run `uv run python -c "import evidently"`. If it fails, either pin `pandas<3` (check this does not break the rest of the project) or wait for a pandas 3 compatible Evidently release.

---

## 3. Core idea: reference vs current

Evidently compares two datasets, column by column.

| Dataset | Role | In this project |
|---|---|---|
| **Reference** | What the model was trained on, the "normal" | `train.csv` from data ingestion |
| **Current** | New data to check | A fresh batch of production data, or the test split in a trial run |

For each column it runs a **statistical test** that asks: "do these two samples come from the same distribution?". Each column is flagged as drifted or not. Then the report counts how many columns drifted.

```
reference data ─┐
                ├──> per-column drift test ──> drifted? ──> share of drifted columns ──> dataset drift?
current data  ──┘
```

---

## 4. Minimal working example

```python
import pandas as pd
from evidently import Report, Dataset, DataDefinition
from evidently.presets import DataDriftPreset

reference = pd.read_csv("Artifacts/notebooks/train.csv")
current = pd.read_csv("Artifacts/notebooks/test.csv")   # replace with real new data

features = [c for c in reference.columns if c != "Result"]

# Tell Evidently what each column IS. Our features are codes (-1/0/1), not magnitudes.
definition = DataDefinition(categorical_columns=features + ["Result"])

ref_ds = Dataset.from_pandas(reference, data_definition=definition)
cur_ds = Dataset.from_pandas(current, data_definition=definition)

report = Report([DataDriftPreset()])
snapshot = report.run(cur_ds, ref_ds)      # order: current first, reference second

snapshot.save_html("drift_report.html")    # visual report
result = snapshot.dict()                   # machine-readable result
```

### Things to know about this API

- **Argument order is `run(current, reference)`.** Swapping them gives wrong comparisons silently.
- **`DataDefinition` matters.** If you skip it, Evidently guesses types. Our `-1/0/1` columns could be guessed as numerical. Declaring them categorical makes the intent explicit.
- **Why categorical here?** `-1/0/1` are labels for "suspicious / neutral / legitimate", not quantities. The same reasoning led us to one-hot encode in notebook 04.
- `snapshot.save_html(...)` produced a ~4 MB file with the full interactive report. Save it as an artifact, not in git.

---

## 5. Which statistical test does it use?

If you do not choose, Evidently picks per column from the sample size and column type:

| Rows in reference | Categorical column | Numerical column |
|---|---|---|
| **<= 1000** | Chi-square test (z-test if only 2 values) | KS test |
| **> 1000** | **Jensen-Shannon distance** | Wasserstein distance |

Our reference has 8,844 rows and categorical columns, so it uses **Jensen-Shannon distance** with a default **threshold of 0.1**. This shows in the metric name: `ValueDrift(column=..., method=Jensen-Shannon distance, threshold=0.1)`.

- **Distance-based tests** (Jensen-Shannon, Wasserstein, PSI): a column drifts when the distance is **at or above** the threshold.
- **p-value tests** (chi-square, KS): a column drifts when the p-value is **below** the threshold (0.05 by default).

On big datasets p-value tests flag tiny, harmless differences as significant, which is why Evidently switches to distance measures above 1,000 rows.

### Overriding the method

```python
DataDriftPreset(
    cat_method="psi",                          # all categorical columns
    cat_threshold=0.2,
    per_column_method={"SSLfinal_State": "jensenshannon"},
    per_column_threshold={"SSLfinal_State": 0.05},   # be stricter on the key feature
    drift_share=0.3,                           # dataset drifts if 30% of columns drift
)
```

`DataDriftPreset` parameters: `columns`, `drift_share`, `method`, `cat_method`, `num_method`, `per_column_method`, `threshold`, `cat_threshold`, `num_threshold`, `per_column_threshold`.

---

## 6. Reading the result (with real output)

### Experiment

1. **Clean check:** reference = train split, current = test split. Both come from the same data, so there should be no drift.
2. **Injected drift:** in the test split, 60% of rows had `SSLfinal_State` and `URL_of_Anchor` forced to `-1`, simulating the two key signals changing.

### What came back

Clean run:

```
DriftedColumnsCount(drift_share=0.5)  -> {"count": 0.0, "share": 0.0}
having_IP_Address   JS distance 0.0077   (threshold 0.1)  -> no drift
URL_Length          JS distance 0.0219                    -> no drift
```

Injected drift:

```
DriftedColumnsCount  -> {"count": 2.0, "share": 0.0645}
SSLfinal_State       JS distance 0.283  -> DRIFT
URL_of_Anchor        JS distance 0.293  -> DRIFT
```

### The trap: dataset-level drift can be "no" while the key features drifted

2 of 31 columns drifted, a share of **0.0645**. The default `drift_share=0.5` needs 50% of columns to drift before the **dataset** counts as drifted, so the dataset-level verdict is **not drifted**, even though the two most important features moved a lot.

What to do:

- **Lower `drift_share`** (I used `0.05` in the second run), and/or
- **Check important columns individually**, which is the better approach. A model that depends on 2 features should alert when either one drifts.

### Extracting drifted columns from the result

`snapshot.dict()` returns `{"metrics": [...], "tests": [...]}`. The first metric is the dataset summary. Each following `ValueDrift` metric holds one column's distance.

```python
def get_drifted_columns(snapshot) -> dict[str, float]:
    """Return {column: distance} for every column at or above its threshold."""
    drifted = {}
    for metric in snapshot.dict()["metrics"]:
        cfg = metric["config"]
        if cfg["type"].endswith("ValueDrift") and metric["value"] >= cfg["threshold"]:
            drifted[cfg["column"]] = float(metric["value"])
    return drifted

get_drifted_columns(snapshot)
# {'SSLfinal_State': 0.283, 'URL_of_Anchor': 0.293}
```

> This helper assumes a distance-based method (drift = value >= threshold). If you switch to a p-value test such as chi-square, the condition flips to `value < threshold`.

`tests` was empty in my run because test conditions are off by default. Pass `include_tests=True` to `Report(...)` if you want pass/fail results.

---

## 7. Fitting it into this project

Follow the project conventions: logger from `app.logging.logger`, custom exception, config via the entity layer, small functions.

### Suggested layout

```
app/
  components/data_drift.py          # DataDrift component
  entity/config_entity.py           # + DataDriftConfig
  entity/artifact_entity.py         # + DataDriftArtifact
  constants/training_pipeline/      # + drift constants
Artifacts/<timestamp>/data_drift/   # html + json report
```

### Constants

```python
DATA_DRIFT_DIR_NAME: str = "data_drift"
DATA_DRIFT_REPORT_HTML: str = "drift_report.html"
DATA_DRIFT_SHARE_THRESHOLD: float = 0.3
DATA_DRIFT_CRITICAL_COLUMNS: list[str] = ["SSLfinal_State", "URL_of_Anchor"]
```

### Artifact

```python
class DataDriftArtifact(BaseModel):
    drift_detected: bool
    drifted_columns: dict[str, float]
    report_path: Path
```

### Component sketch

```python
import sys
from pathlib import Path

import pandas as pd
from evidently import Report, Dataset, DataDefinition
from evidently.presets import DataDriftPreset

from app.constants import training_pipeline as tp
from app.entity.artifact_entity import DataDriftArtifact
from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger


class DataDrift:
    def __init__(self, reference_path: Path, current_path: Path, report_dir: Path) -> None:
        self.reference_path = reference_path
        self.current_path = current_path
        self.report_dir = report_dir

    def initiate_data_drift(self) -> DataDriftArtifact:
        try:
            reference = pd.read_csv(self.reference_path)
            current = pd.read_csv(self.current_path)

            features = [c for c in reference.columns if c != tp.TARGET_COLUMN]
            definition = DataDefinition(categorical_columns=features + [tp.TARGET_COLUMN])

            report = Report([DataDriftPreset(drift_share=tp.DATA_DRIFT_SHARE_THRESHOLD)])
            snapshot = report.run(
                Dataset.from_pandas(current, data_definition=definition),
                Dataset.from_pandas(reference, data_definition=definition),
            )

            self.report_dir.mkdir(parents=True, exist_ok=True)
            report_path = self.report_dir / tp.DATA_DRIFT_REPORT_HTML
            snapshot.save_html(str(report_path))

            drifted = self._drifted_columns(snapshot)
            critical = set(drifted) & set(tp.DATA_DRIFT_CRITICAL_COLUMNS)
            share = len(drifted) / len(features)
            drift_detected = bool(critical) or share >= tp.DATA_DRIFT_SHARE_THRESHOLD

            logger.info(f"Drifted columns: {drifted} | share={share:.2%} | critical={critical}")
            return DataDriftArtifact(
                drift_detected=drift_detected,
                drifted_columns=drifted,
                report_path=report_path,
            )
        except Exception as e:
            logger.exception("Data drift detection failed")
            raise NetworkSecurityException(e, sys) from e

    @staticmethod
    def _drifted_columns(snapshot) -> dict[str, float]:
        drifted = {}
        for metric in snapshot.dict()["metrics"]:
            cfg = metric["config"]
            if cfg["type"].endswith("ValueDrift") and metric["value"] >= cfg["threshold"]:
                drifted[cfg["column"]] = float(metric["value"])
        return drifted
```

Note `drift_detected` triggers on **either** a critical feature drifting **or** the overall share passing the limit. This is what avoids the trap from section 6.

### Where to call it

| Moment | Reference | Current | Action on drift |
|---|---|---|---|
| **Training pipeline**, after ingestion | Previous run's `train.csv` | New `train.csv` | Warn, log, and review before retraining |
| **Batch monitoring** (daily / weekly job) | The model's `train.csv` | Last N days of production inputs | Alert, then consider retraining |
| **FastAPI service** | Same as above | Log requests to MongoDB, read them back in a scheduled job | Alert. Do not compute drift per request |

Compute drift on **batches** (hundreds to thousands of rows). Drift tests on a handful of rows are meaningless.

---

## 8. Practical advice

1. **Pick the reference carefully.** Use the training data of the model currently deployed. After retraining, update it.
2. **Use enough rows.** With fewer than about 300 current rows, results are noisy.
3. **Tune thresholds on your own data.** First run the report on two samples you know are from the same period (like our train vs test: all distances were below 0.03). That shows the natural noise level, so you can set a threshold above it.
4. **Weight by importance.** Alert on the features the model relies on (`SSLfinal_State`, `URL_of_Anchor`) more strictly than on weak ones. Importance came from notebooks 03 and 05.
5. **Drift is a signal, not proof of failure.** Check the model's accuracy on newly labelled data before deciding to retrain.
6. **Also watch the target.** If labels are available, include `Result` in the check, as in the example, to catch target drift.
7. **Keep reports out of git.** They are large (about 4 MB). `Artifacts/` is already in `.gitignore`.

---

## 9. Quick checklist

- [ ] Resolve the pandas / Evidently version conflict (section 2)
- [ ] Declare the columns in `DataDefinition` (categorical here)
- [ ] Call `report.run(current, reference)` in that order
- [ ] Do not rely only on dataset-level drift. Check key columns, as in section 6
- [ ] Save the HTML report and log drifted columns with `logger`
- [ ] Run on batches, not single requests

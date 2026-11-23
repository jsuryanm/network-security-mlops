# Model Trainer: Errors and Fixes

Debugging notes from wiring up `RandomizedSearchCV` in the model trainer stage.
Each section gives the symptom, the root cause, the fix, and the file it lives in.

Files involved:

| File | Role |
|---|---|
| `app/components/model_trainer.py` | `ModelTrainer`: builds models and param distributions, picks the best model, saves it |
| `app/utils/main_utils/utils.py` | `evaluate_models`, `load_object`, `save_object` helpers |
| `app/entity/config_entity.py` | `ModelTrainerConfig`: where artifacts are written |
| `notebooks/08_model_trainer.ipynb` | Prototype of the same search |

---

## 1. `FutureWarning: 'n_jobs' has no effect` (LogisticRegression)

**File:** `notebooks/08_model_trainer.ipynb`

**Symptom**

```
FutureWarning: 'n_jobs' has no effect since 1.8 and will be removed in 1.10.
You provided 'n_jobs=-1', please leave it unspecified.
```

**Cause.** Since scikit-learn 1.8, `LogisticRegression` ignores `n_jobs`. It was
passed as `LogisticRegression(n_jobs=-1)`, so every fit emitted the warning.
`RandomizedSearchCV` fits each model many times, so the warning repeated dozens of times.

**Fix.** Removed `n_jobs=-1` from `LogisticRegression`. Parallelism still comes from
`RandomizedSearchCV(n_jobs=-1)`, where it does work. `max_iter=1000` was kept so the
solver converges.

---

## 2. `param_distribs` was incomplete and mis-keyed

**File:** `app/components/model_trainer.py`

**Symptoms**

- A `SyntaxError`: the last entry was `"XGBoost Classifier":` with no value, and the
  dict had no closing `}`.
- A latent `KeyError`: `models` used the key `"Adaboost"` but `param_distribs` used `"AdaBoost"`.

**Cause.** `evaluate_models` loops over `models.keys()` and does `params[key]`.
Every key in `models` must exist, spelled identically, in the params dict.

**Fix.**

- Added a real distribution dict for XGBoost.
- Renamed the params key to `"Adaboost"` to match `models`.
- Closed the dict.

**Why distributions, not lists.** `RandomizedSearchCV` accepts either lists (sampled
uniformly) or scipy distributions (sampled from a continuous or integer range):

| Distribution | Meaning | Used for |
|---|---|---|
| `randint(a, b)` | integers `a` to `b-1` (upper bound exclusive) | `n_estimators`, `max_depth`, `min_samples_*` |
| `uniform(loc, scale)` | continuous `[loc, loc+scale]` | `subsample`, `colsample_bytree`, `gamma` |
| `loguniform(a, b)` | continuous, uniform in log space | `learning_rate`, `C` |

`uniform(0.6, 0.4)` therefore covers 0.6 to 1.0, not 0.6 to 0.4. Log-uniform is used
for `learning_rate` and `C` because they matter multiplicatively: 0.001 to 0.01 is
as meaningful as 0.1 to 1.

---

## 3. `UnboundLocalError: best_model_name`

**File:** `app/components/model_trainer.py`, `train_model`

**Symptom**

```
UnboundLocalError: cannot access local variable 'best_model_name'
where it is not associated with a value
```

All the `[Parallel]` log lines before it were the successful tuning. The crash came
after `evaluate_models` returned.

**Cause.** The code read the variable one line before assigning it:

```python
best_model_score = models[best_model_name]       # read here ...
best_model_name = list(model_report.keys())[...] # ... assigned here
```

Python runs lines in order, so the name does not exist yet on the first line. The
error is `UnboundLocalError` and not `NameError` because Python marks any name that
is assigned anywhere in a function as local to that function when it compiles it.

**Fix.** Removed the premature line and found the best model by name directly:

```python
best_model_name = max(model_report, key=model_report.get)
best_model = models[best_model_name]
```

`max(d, key=d.get)` returns the key with the highest value. It is simpler than the
original `list(...).index(value)` lookup and does not break on ties.

---

## 4. `best_model` was a float, not a model

**File:** `app/components/model_trainer.py`

**Cause.** `model_report` maps `name -> score`. The code then did
`best_model = model_report[best_model_name]`, which returns a float, so the next
line `best_model.predict(...)` would fail with
`'float' object has no attribute 'predict'`.

**Fix.** Read the fitted model from the `models` dict instead.
`evaluate_models` calls `model.set_params(**best_params)` and `model.fit(...)` on the
same objects in `models`, so `models[best_model_name]` is already the tuned, fitted model.

---

## 5. `evaluate_models` built a wrong report

**File:** `app/utils/main_utils/utils.py`

Two separate bugs.

**5a. The report key was a model object.**

```python
report[models.get(key)] = test_model_score   # key is an estimator instance
```

It must be the model name, or the best name cannot be looked up later. Fixed to
`report[key] = test_model_score`.

**5b. Swapped arguments to `precision_score`.**

```python
precision_score(y_train_pred, y_train)   # wrong order
```

scikit-learn's signature is `precision_score(y_true, y_pred)`. With the arguments
swapped, the function computes recall instead of precision. This did not crash, but
the scores used to rank models were wrong. Fixed to
`precision_score(y_train, y_train_pred)` and `precision_score(y_test, y_test_pred)`.

**Related design note.** The best model is chosen on test-set precision. That leaks
test data into model selection. A cleaner approach is to rank by
`rnd_search.best_score_` (the cross-validated score) and keep the test set only for
the final report.

---

## 6. Problems that would have failed right after the crash

Once the `UnboundLocalError` was fixed, these were next in line.

| # | File | Problem | Fix |
|---|---|---|---|
| 6a | `model_trainer.py` | `NetworkModel(preprocessor=preprocessor)` omitted `model`, but `NetworkModel.__init__(preprocessor, model)` requires it, so it raised `TypeError`. A saved wrapper with no model could not predict anyway. | `NetworkModel(preprocessor=preprocessor, model=best_model)` |
| 6b | `utils.py` | `load_object(file_path, file_obj)` required a second argument that callers never passed (`TypeError`). | Signature is now `load_object(file_path)` |
| 6c | `utils.py` | `Path(file_path).exists` without `()` is a method object, always truthy, so the missing-file check never fired. | Call `.exists()`, raise `FileNotFoundError` |
| 6d | `utils.py` | Leftover `print(file_obj)`. Project rule is to log, not print. | Removed |
| 6e | `model_trainer.py` | `os.makedirs(model_dir_path)` where the path was the model file path, so it would create `model.pkl` as a directory and the later `open(..., "wb")` would fail with `IsADirectoryError`. `save_object` already creates the parent directory. | Removed the call, and the now-unused `os` and `Path` imports |
| 6f | `model_trainer.py` | `verbose=1` on Random Forest and Logistic Regression produced hundreds of `[Parallel]` lines during the search. | Removed `verbose=1` |

A security note on `load_object`: `joblib.load` can run arbitrary code from a
malicious pickle. It is safe here because it only loads files this pipeline wrote
under `Artifacts/`. Never point it at files from outside the project.

---

## 7. `RecursionError` in `ModelTrainerConfig`

**File:** `app/entity/config_entity.py`, `ModelTrainerConfig`

**Symptom**

```
File ".../config_entity.py", line 198, in model_trainer_dir
    self.model_trainer_dir /
[Previous line repeated 993 more times]
RecursionError: maximum recursion depth exceeded
```

It surfaced at `save_object(file_path=self.model_trainer_config.trained_model_file_path, ...)`.
Training and tuning had already finished. The crash came when the save path was requested.

**Cause.** The property referred to itself:

```python
@property
def model_trainer_dir(self) -> Path:
    return self.model_trainer_dir / MODEL_TRAINER_DIR_NAME
```

Reading `self.model_trainer_dir` runs the property, which reads
`self.model_trainer_dir`, and so on until Python's recursion limit. Properties look
like plain attributes, which makes this easy to write by accident. The model is a
frozen Pydantic model with no field of that name, so there was nothing to fall back to.

**Fix.** Build the directory from the artifact root, the same pattern
`data_transformation_dir` uses:

```python
@property
def model_trainer_dir(self) -> Path:
    return (
        self.training_pipeline_config.artifact_dir /
        training_pipeline.MODEL_TRAINER_DIR_NAME
    )
```

**Second bug in the same class.** `trained_model_file_path` appended
`MODEL_TRAINER_DIR_NAME` again, although `model_trainer_dir` already ends with it.
It would have produced `model_trainer/model_trainer/trained_model/model.pkl`.
Removed the duplicate segment. The final path is:

```
Artifacts/<timestamp>/model_trainer/trained_model/model.pkl
```

---

## Takeaways

1. **Read the traceback from the bottom up, but find where the work stopped.** In #3 and #7 the expensive step (tuning) had succeeded. The failure was in cheap glue code after it.
2. **Keys must match across parallel dicts.** `models` and `param_distribs` are looked up by the same string. A typo like `AdaBoost` vs `Adaboost` fails only at run time.
3. **Check argument order on metrics.** `(y_true, y_pred)` for every sklearn metric. Swapping them often produces plausible-looking wrong numbers.
4. **Keep properties from reading themselves.** Derive each path property from a different, already-defined source.
5. **Silent bugs matter more than crashes.** #5b (swapped precision arguments) and #6c (missing `()` on `.exists`) would not have raised an error but would have given wrong results.

import yaml
import joblib 
import os 
import sys 
from pathlib import Path 

import numpy as np 
import joblib

from sklearn.base import BaseEstimator
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import precision_score
from scipy.stats import randint, uniform, loguniform


from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger 

def read_yaml_file(file_path: Path) -> dict:
    try: 
        with open(file_path, 'rb') as yaml_file: 
            return yaml.safe_load(yaml_file)
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def write_yaml_file(
    file_path: Path,
    content: object,
    replace: bool = True,
) -> None:
    """Write `content` as YAML. Creates parent dirs; overwrites when replace=True."""
    try:
        file_path = Path(file_path)
        if file_path.exists() and not replace:
            return
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as file:
            yaml.dump(content, file)

    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def save_numpy_array_data(file_path: Path, array: np.array):
    """Save numpy array data to file
    file_path: str location of the file, 
    array: np.array to save"""
    try:
        dir_path = Path(file_path).parent
        os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'wb') as file_obj:
            np.save(file_obj, array)
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def save_object(file_path: Path, obj: object) -> None:
    try:
        os.makedirs(os.path.dirname(file_path),exist_ok=True)
        with open(file_path, 'wb') as file_obj:
            joblib.dump(obj,file_obj)
    
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e 

def evaluate_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    models: dict,
    params: dict
) -> dict:
    """Performs hyperparameter tuning on various 
    models. The models are then trained and evaluated, we will 
    return dict containing the models performance"""
    try:
        report = dict()

        for key in models.keys():
            model = models[key]
            param = params[key]

            rnd_search = RandomizedSearchCV(
                model,
                param_distributions=param,
                n_iter=10,          # random combos sampled per model
                cv=3,
                scoring="precision",
                n_jobs=-1,
                random_state=42,
            )

            rnd_search.fit(X_train, y_train)

            best_params = rnd_search.best_params_
            model.set_params(**best_params)
            model.fit(X_train)

            y_train_pred = model.predict(X_train)
            y_test_pred = model.predict(X_test)

            train_model_score = precision_score(y_train_pred, y_train)
            test_model_score = precision_score(y_test_pred, y_test)

            report[models.get(key)] = test_model_score

        return report

    except Exception as e:
        raise NetworkSecurityException(e, sys)
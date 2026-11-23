import sys 

import numpy as np
from scipy.stats import loguniform, randint, uniform

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier
)
from sklearn.model_selection import RandomizedSearchCV

from xgboost import XGBClassifier

import mlflow
from urllib.parse import urlparse

import dagshub

from app.logging.logger import logger 
from app.exception.exceptions import NetworkSecurityException

from app.entity.config_entity import (
    DataTransformationConfig,
    ModelTrainerConfig
)

from app.entity.artifact_entity import (
    DataTransformationArtifact,
    ModelTrainerArtifact
)

from app.utils.ml_utils.estimator import NetworkModel
from app.utils.main_utils.utils import (
    save_object,
    load_object,
    load_numpy_array_data,
    evaluate_models
)

from app.utils.ml_utils.classification_metric import get_classification_score


class ModelTrainer:
    def __init__(
        self,
        model_trainer_config: ModelTrainerConfig,
        data_transformation_artifact: DataTransformationArtifact
    ):
        try:
            self.model_trainer_config = model_trainer_config 
            self.data_transformation_artifact = data_transformation_artifact

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ):
        models = {
            "Random Forest": RandomForestClassifier(
                random_state=42,
                n_jobs=-1
            ),
            "XGBoost Classifier": XGBClassifier(),
            "Decision Tree": DecisionTreeClassifier(random_state=42),
            "Gradient Boosting": GradientBoostingClassifier(random_state=42),
            "Logistic Regression": LogisticRegression(
                random_state=42,
                max_iter=1000
            ),
            "Adaboost": AdaBoostClassifier(random_state=42)
        }

        param_distribs = {
            "Decision Tree": {
                "criterion": ["gini", "entropy", "log_loss"],
                "splitter": ["best", "random"],
                "max_depth": randint(3, 30),
                "min_samples_split": randint(2, 20),
                "min_samples_leaf": randint(1, 10),
                "max_features": ["sqrt", "log2", None],
            },
            "Random Forest": {
                "n_estimators": randint(50, 500),
                "max_depth": [None] + list(range(5, 31, 5)),
                "min_samples_split": randint(2, 20),
                "min_samples_leaf": randint(1, 10),
                "max_features": ["sqrt", "log2", None],
            },
            "Gradient Boosting": {
                "n_estimators": randint(50, 500),
                "learning_rate": loguniform(1e-3, 3e-1),
                "subsample": uniform(0.6, 0.4),  # U[0.6, 1.0]
                "max_depth": randint(2, 8),
                "min_samples_leaf": randint(1, 10),
                "max_features": ["sqrt", "log2", None],
            },
            "Logistic Regression": {
                "C": loguniform(1e-3, 1e2),
            },
            "Adaboost": {
                "n_estimators": randint(50, 500),
                "learning_rate": loguniform(1e-3, 1),
            },
            "XGBoost Classifier": {
                "n_estimators": randint(100, 600),
                "learning_rate": loguniform(1e-2, 3e-1),
                "max_depth": randint(3, 10),
                "min_child_weight": randint(1, 10),
                "subsample": uniform(0.6, 0.4),         # U[0.6, 1.0]
                "colsample_bytree": uniform(0.6, 0.4),  # U[0.6, 1.0]
                "gamma": uniform(0, 0.5),
            },
        }

        model_report: dict = evaluate_models(
            X_train=X_train, 
            y_train=y_train, 
            X_test=X_test, 
            y_test=y_test,
            models=models,
            params=param_distribs
        )

        best_model_name = max(model_report, key=model_report.get)
        logger.info(f"Best Model: {best_model_name} | Precision: {model_report[best_model_name]:.4f}")

        best_model = models[best_model_name]
        y_train_pred = best_model.predict(X_train)
        y_test_pred = best_model.predict(X_test)

        classification_train_metric = get_classification_score(
            y_true=y_train,
            y_pred=y_train_pred
        )

        
        classification_test_metric = get_classification_score(
            y_true=y_test,
            y_pred=y_test_pred
        )

        preprocessor = load_object(file_path=self.data_transformation_artifact.transformed_object_file_path)
        network_model = NetworkModel(preprocessor=preprocessor, model=best_model)
        save_object(file_path=self.model_trainer_config.trained_model_file_path, obj=network_model)

        model_trainer_artifact = ModelTrainerArtifact(
            trained_model_file_path=self.model_trainer_config.trained_model_file_path,
            trained_metric_artifact=classification_train_metric,
            test_metric_artifact=classification_test_metric
        )

        logger.info(f"Model trainer artifact: {model_trainer_artifact}")

        return model_trainer_artifact


    
    def initiate_model_trainer(self) -> ModelTrainerArtifact:
        try:
            train_file_path = self.data_transformation_artifact.transformed_train_file_path
            test_file_path = self.data_transformation_artifact.transformed_test_file_path

            train_arr = load_numpy_array_data(train_file_path)
            test_arr = load_numpy_array_data(test_file_path)

            X_train, y_train, X_test, y_test = (
                train_arr[:, :-1],
                train_arr[:, -1],
                test_arr[:, :-1],
                test_arr[:, -1],
            )

            model_trainer_artifact = self.train_model(
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test
            )

            return model_trainer_artifact

        except Exception as e:
            raise NetworkSecurityException(e, sys)
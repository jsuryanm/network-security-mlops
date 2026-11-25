import os 
import sys 

import numpy as np 
import pandas as pd 
from pathlib import Path 

# common constant variables for training pipeline 
TARGET_COLUMN: str = "Result"
PIPELINE_NAME: str = "NetworkSecurity"
ARTIFACT_DIR: str = "Artifacts"
FILE_NAME: str = "NetworkData.csv"

TRAIN_FILE_NAME: str = "train.csv"
TEST_FILE_NAME: str = "test.csv"

SCHEMA_FILE_PATH: Path = Path('data_schema') / "schema.yaml"

SAVED_MODEL_DIR: Path = Path('saved_models')
MODEL_FILE_NAME: str = "model.pkl"



# Data ingestion related constants 
DATA_INGESTION_COLLECTION_NAME: str = "NetworkData"
DATA_INGESTION_DATABASE_NAME: str = "Surya"
DATA_INGESTION_DIR_NAME: str = "data_ingestion" 
DATA_INGESTION_FEATURE_STORE_DIR: str = "feature_store"
DATA_INGESTION_INGESTED_DIR: str = "ingested"
DATA_INGESTION_TRAIN_TEST_SPLIT_RATIO: float = 0.2

# Data validation constants
DATA_VALIDATION_DIR_NAME: str = "data_validation"
DATA_VALIDATION_VALID_DIR: str = "validated"
DATA_VALIDATION_INVALID_DIR: str = "invalid"
DATA_VALIDATION_DRIFT_REPORT_DIR: str = "drift_report"
DATA_VALIDATION_DRIFT_REPORT_FILE_NAME: str = "report.yaml" 
DATA_VALIDATION_DRIFT_HTML_FILE_NAME: str = "report.html"

# Data drift (Evidently): compare train (reference) vs test (current)
DATA_DRIFT_METHOD: str = "jensenshannon"   # distance test: drift when distance >= threshold
DATA_DRIFT_THRESHOLD: float = 0.1          # per-column threshold
DATA_DRIFT_SHARE: float = 0.3              # dataset drifts when >= 30% of columns drift
DATA_DRIFT_CRITICAL_COLUMNS: list[str] = ["SSLfinal_State", "URL_of_Anchor"]  # model depends on these (notebook 05)

# Data transformation constants
DATA_TRANSFORMATION_DIR_NAME: str = "data_transformation"
DATA_TRANSFORMATION_TRANSFORMED_DATA_DIR: str = "transformed"
DATA_TRANSFORMATION_TRANSFORMED_OBJECT_DIR: str = "transformed_object"
DATA_TRANSFORMATION_IMPUTE_PARAMS: dict = {
    "missing_values": np.nan, # nan values will be imputed
    "n_neighbors": 3,  # no of neighbor samples used for imputation
    "weights": "uniform" # weights assigned to neighbors
}  
DATA_TRANSFORMATION_TRAIN_FILE_PATH: str = "train.npy"
DATA_TRANSFORMATION_TEST_FILE_PATH: str = "test.npy"
PREPROCESSING_OBJECT_FILE_NAME: str = "preprocessing.pkl"

# Model Trainer constants
MODEL_TRAINER_DIR_NAME: str = "model_trainer"
MODEL_TRAINER_TRAINED_MODEL_DIR: str = "trained_model"
MODEL_TRAINER_TRAINED_MODEL_NAME: str = "model.pkl"
MODEL_TRAINER_EXPECTED_SCORE: float = 0.6
MODEL_TRAINER_OVER_FIITING_UNDER_FITTING_THRESHOLD: float = 0.05


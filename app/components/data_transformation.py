import sys 
import os 
from pathlib import Path 

import numpy as np 
import pandas as pd 
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline

from app.core.config import get_settings
from app.logging.logger import logger 

from app.constants.training_pipeline import (
    TARGET_COLUMN,
    DATA_TRANSFORMATION_IMPUTE_PARAMS
)
from app.entity.artifact_entity import (
    DataValidationArtifact,
    DataTranformationArtifact
)

from app.entity.config_entity import DataTransformationConfig
from app.utils.main_utils.utils import save_numpy_array_data, save_object
from app.exception.exceptions import NetworkSecurityException

class DataTransformation:
    def __init__(
            self,
            data_validation_artifact: DataValidationArtifact,
            data_transformation_config: DataTransformationConfig
    ):
        try:
            self.data_validation_artifact = data_validation_artifact
            self.data_transformation_config = data_transformation_config
        except Exception as e:
            raise NetworkSecurityException(e, sys) from e 

    @staticmethod 
    def read_data(file_path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise NetworkSecurityException(e, sys)
    
    def initiate_data_transformation(self) -> DataTranformationArtifact:
        try:
            logger.info("Performing the data transformation")
            train_df = DataTransformation.read_data()
        except Exception as e:
            raise NetworkSecurityException(e, sys)

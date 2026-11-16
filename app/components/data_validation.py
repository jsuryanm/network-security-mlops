import sys
from pathlib import Path 
import os 
import pandas as pd

from app.logging.logger import logger 
from app.exception.exceptions import NetworkSecurityException
from app.core.config import get_settings
from app.constants.training_pipeline import SCHEMA_FILE_PATH

from app.entity.config_entity import DataValidationConfig
from app.entity.artifact_entity import (
    DataIngestionArtifact,
    DataValidationArtifact
)
from app.utils.main_utils.utils import read_yaml_file

from scipy.stats import ks_2samp

class DataValidation:
    def __init__(
        self,
        data_ingestion_artifact: DataIngestionArtifact,
        data_validation_config: DataValidationConfig,
    ):
        try:
            self.data_ingestion_artifact = data_ingestion_artifact
            self.data_validation_config = data_validation_config
            self._schema_config = read_yaml_file(SCHEMA_FILE_PATH)

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    @staticmethod
    def read_data(file_path) -> pd.DataFrame:
        """Reads pandas dataframe"""
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def validate_num_columns(self, dataframe: pd.DataFrame) -> bool:
        try:
            num_cols = len(self._schema_config)
            logger.info(f"Required number of columns: {num_cols}")
            logger.info(f"Dataframe has columns: {len(dataframe.columns)}")

            if num_cols == len(dataframe.columns):
                return True
             
            return False
        except Exception as e:
            raise NetworkSecurityException

    def detect_data_drift(
        self,
        base_df,
        current_df,
        threshold=0.05
    ) -> bool:
        try:
            status = True 
            report = {}
            for column in base_df.columns:
                df1 = base_df[column]
                df2 = current_df[column]
                ks_2samp(df1,df2)

        except Exception as e:
            raise NetworkSecurityException(e, sys)


    def initiate_data_validation(self) -> DataValidationArtifact:
        """Starts the data validation pipeline"""
        try:
            train_file_path = self.data_ingestion_artifact.trained_file_path
            test_file_path = self.data_ingestion_artifact.test_file_path
        
            train_dataframe = DataValidation.read_data(train_file_path)
            test_dataframe = DataValidation.read_data(test_file_path)
            
            status = self.validate_num_columns(dataframe=train_dataframe)
            if not status:
                error_message = f"train df does not contain all the columns.\n"

            status = self.validate_num_columns(dataframe=test_dataframe)
            if not status:
                error_message = f"test df does not contain all columns.\n"

            # data drift check 
        

        except Exception as e:
            raise NetworkSecurityException(e, sys)
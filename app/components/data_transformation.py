import sys 
import os 
from pathlib import Path 

import numpy as np 
import pandas as pd 
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline

from app.logging.logger import logger 

from app.constants.training_pipeline import (
    TARGET_COLUMN,
    DATA_TRANSFORMATION_IMPUTE_PARAMS
)
from app.entity.artifact_entity import (
    DataValidationArtifact,
    DataTransformationArtifact
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

    def get_data_transformer_object(cls) -> Pipeline:
        """Initiatlizes KNNImputer obj with params from training_pipeline.py 
        and returns sklearn Pipeline object"""
        try:
            imputer : KNNImputer = KNNImputer(**DATA_TRANSFORMATION_IMPUTE_PARAMS)
            
            logger.info(f"Initiatlize KNN imputer with {DATA_TRANSFORMATION_IMPUTE_PARAMS}")

            processor: Pipeline = Pipeline([('imputer',imputer)])
            return processor 

        except Exception as e:
            raise NetworkSecurityException(e, sys)
     
    def initiate_data_transformation(self) -> DataTransformationArtifact:
        try:
            logger.info("Performing the data transformation")
 
            train_df = DataTransformation.read_data(self.data_validation_artifact.valid_train_file_path)
            test_df = DataTransformation.read_data(self.data_validation_artifact.valid_test_file_path)
 
            input_feature_train_df = train_df.drop(columns=[TARGET_COLUMN],axis=1)
            target_feature_train_df = train_df[TARGET_COLUMN]
            target_feature_train_df = target_feature_train_df.replace(-1,0)

            input_feature_test_df = test_df.drop(columns=[TARGET_COLUMN],axis=1)
            target_feature_test_df = test_df[TARGET_COLUMN]
            target_feature_test_df = target_feature_test_df.replace(-1, 0)

            preprocessor = self.get_data_transformer_object()

            preprocessor_obj = preprocessor.fit(input_feature_train_df)
            transformed_input_train_feature = preprocessor_obj.transform(input_feature_train_df)
            transformed_input_test_feature = preprocessor_obj.transform(input_feature_test_df)

            train_arr = np.c_[transformed_input_train_feature, np.array(target_feature_train_df)]
            test_arr = np.c_[transformed_input_test_feature, np.array(target_feature_test_df)]

            save_numpy_array_data( self.data_transformation_config.transformed_train_file_path, array=train_arr, )
            save_numpy_array_data( self.data_transformation_config.transformed_test_file_path,array=test_arr,)
            
            save_object( self.data_transformation_config.transformed_object_file_path, preprocessor_obj)

            final_model_path = Path("final_models")
            final_model_path.mkdir(parents=True, exist_ok=True)
            save_object(final_model_path / "preprocessor.pkl", preprocessor_obj)
            
            logger.info("Saving the transformed training and test data and Imputer object.")

            data_transformation_artifact =  DataTransformationArtifact(
                transformed_object_file_path=self.data_transformation_config.transformed_object_file_path,
                transformed_train_file_path=self.data_transformation_config.transformed_train_file_path,
                transformed_test_file_path=self.data_transformation_config.transformed_test_file_path
            )

            return data_transformation_artifact

        except Exception as e:
            raise NetworkSecurityException(e, sys)


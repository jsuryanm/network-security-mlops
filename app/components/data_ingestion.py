import os 
from pathlib import Path
from typing import List
import sys

from app.core.config import get_settings 
from app.entity.config_entity import DataIngestionConfig
from app.entity.artifact_entity import DataIngestionArtifact

from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger 
 
from sklearn.model_selection import train_test_split
import pymongo

import pandas as pd
import numpy as np

settings = get_settings()

class DataIngestion:
    def __init__(
        self,
        data_ingestion_config: DataIngestionConfig
    ):
        try:
            self.data_ingestion_config = data_ingestion_config
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def export_collection_as_frame(self):
        """Export mongodb collection as a dataframe"""
        try:
            database_name = self.data_ingestion_config.database_name
            collection_name = self.data_ingestion_config.collection_name
                        
            self.mongo_client = pymongo.MongoClient(settings.mongodb_uri)
            collection =  self.mongo_client[database_name][collection_name]
            
            df = pd.DataFrame(list(collection.find()))
            
            if "_id" in df.columns.to_list():
                df = df.drop(columns=['_id'])

            df = df.replace({'na':np.nan})
            return df
                    
        except Exception as e:
            raise NetworkSecurityException(e, sys)
        
    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        """Reads the data from MongoDB and returns DataIngestionArtifact"""
        try:
            dataframe = self.export_collection_as_frame()
            dataframe = self.export_data_into_feature_store(dataframe)
            self.split_data_as_train_test(dataframe=dataframe)

            data_ingestion_artifact = DataIngestionArtifact(
                trained_file_path=self.data_ingestion_config.training_file_path,
                test_file_path=self.data_ingestion_config.testing_file_path
            )

            return data_ingestion_artifact

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def export_data_into_feature_store(self, dataframe: pd.DataFrame):
        """Converting the feature store into csv file"""
        try:
            feature_store_file_path = self.data_ingestion_config.feature_store_file_path
            
            dir_path = Path(feature_store_file_path).parent
            os.makedirs(dir_path,exist_ok=True)
            
            dataframe.to_csv(
                feature_store_file_path,
                index=False,
                header=True
            )

            return dataframe

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def split_data_as_train_test(self, dataframe: pd.DataFrame):
        try:
            train_set, test_set = train_test_split(
                dataframe, 
                test_size=self.data_ingestion_config.train_test_split_ratio,
                random_state=42
            )

            logger.info("Performed train test split on the dataframe")
            logger.info("Exited split_data_as_train_test_split()")

            dir_path = Path(self.data_ingestion_config.training_file_path).parent
            os.makedirs(dir_path,exist_ok=True)

            logger.info(f"Exporting the train and test file path.")
            
            train_set.to_csv(
                self.data_ingestion_config.training_file_path,
                index=False,
                header=True
            )

            test_set.to_csv(
                self.data_ingestion_config.testing_file_path,
                index=False,
                header=True
            )


        except Exception as e:
            raise NetworkSecurityException(e, sys)

# if __name__ == "__main__":
#     data_ingestion_artifact = DataIngestion(DataIngestionConfig()).initiate_data_ingestion()
#     print(data_ingestion_artifact)
import os 
from pathlib import Path
from typing import List
import sys

from app.core.config import get_settings 
from app.entity.config_entity import DataIngestionConfig

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
                df = df.drop(columns=['_id'],axis=1)

            df.replace({'na':np.nan})
            return df
                    
        except Exception as e:
            raise NetworkSecurityException(e, sys)
        
    def initiate_data_ingestion(self):
        """Reads the data from MongoDB"""
        try:
            df = self.export_collection_as_frame()
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def export_data_into_feature_store(self, dataframe: pd.DataFrame):
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
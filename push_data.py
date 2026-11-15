import sys 
import os 
import json 

import certifi 
# certifi is a python library that provides Mozilla's collection of root certificates 
# for SSL/TSL certificate validation and host identity validation during HTTPS connections

import numpy as np 
import pandas as pd 
import pymongo

from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger

from app.core.config import get_settings 
from app.exception.exceptions import NetworkSecurityException


settings = get_settings()

ca = certifi.where() 
# returns the local file path cacert.pem root certificate bundle

class NetworkDataExtract():
    def __init__(self):    
        try:
            pass
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def csv_to_json_converter(self, file_path):
        """Convert the dataset from csv to json"""
        try:
            data = pd.read_csv(file_path)
            logger.info(f"Reading {file_path}")
            data = data.reset_index(drop=True)
            records = data.to_dict(orient='records') 
            # converts df into list of dicts
            logger.info(f"First record: {records[0]}")
            return records
        
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def insert_data_mongodb(
        self,
        records,
        database,
        collection    
    ):
        """Push the data to mongodb"""
        try:
            self.database = database
            self.collection = collection
            self.records = records

            self.mongo_client = pymongo.MongoClient(settings.mongodb_uri)
            self.database = self.mongo_client[self.database]
            
            self.collection = self.database[self.collection]
            # collection is container for grouping related data records, (equivalent of table)
            self.collection.insert_many(self.records) # insert a batch of docs into collection

            return len(self.records)

        except Exception as e:
            raise NetworkSecurityException(e, sys) 

if __name__ == "__main__":
    file_path = 'data/phisingData.csv'
    database = "Surya"
    collection = "NetworkData"

    network_obj = NetworkDataExtract()
    records = network_obj.csv_to_json_converter(file_path=file_path)
    
    num_records = network_obj.insert_data_mongodb(
        records=records,
        database=database,
        collection=collection
    )

    print(num_records)
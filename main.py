from app.entity.config_entity import TrainingPipelineConfig
from app.entity.config_entity import DataIngestionConfig, DataValidationConfig

from app.components.data_ingestion import DataIngestion
from app.components.data_validation import DataValidation

from app.exception.exceptions import NetworkSecurityException

from app.logging.logger import logger 

import sys 

if __name__ == "__main__":
    try:
        training_pipeline_config = TrainingPipelineConfig()
        
        data_ingestion_config = DataIngestionConfig(training_pipeline_config=training_pipeline_config)
        data_ingestion = DataIngestion(data_ingestion_config)
        
        logger.info("Initiate the data ingestion")
        data_ingestion_artifact = data_ingestion.initiate_data_ingestion()
        logger.info("Data ingestion completed")

        data_validation_config = DataValidationConfig(training_pipeline_config=training_pipeline_config)
        data_validation = DataValidation(
            data_ingestion_artifact,
            data_validation_config
        )
        
        logger.info("Initiate the data validation")

        data_validation_artifact = data_validation.initiate_data_validation()
        logger.info(f"Data validation completed: {data_validation_artifact}")

    except Exception as e:
        raise NetworkSecurityException(e, sys)
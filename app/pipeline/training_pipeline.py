import os
import sys 

from pathlib import Path 

from app.core.config import get_settings
from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger

from app.components.data_ingestion import DataIngestion
from app.components.data_transformation import DataTransformation
from app.components.data_validation import DataValidation
from app.components.model_trainer import ModelTrainer 

from app.entity.config_entity import (
    TrainingPipelineConfig,
    DataIngestionConfig,
    DataValidationConfig,
    DataTransformationConfig,
    ModelTrainerConfig
)

from app.entity.artifact_entity import (
    DataIngestionArtifact,
    DataValidationArtifact,
    DataTransformationArtifact,
    ModelTrainerArtifact
)

from app.cloud.s3_syncer import S3Sync

settings = get_settings()

class TrainingPipeline:
    def __init__(self):
        self.training_pipeline_config = TrainingPipelineConfig()
        self.s3_sync = S3Sync()

    def start_data_ingestion(self) -> DataIngestionArtifact:
        """Initiate the data ingestion component"""
        try:
            self.data_ingestion_config = DataIngestionConfig(training_pipeline_config=self.training_pipeline_config)
            logger.info("Starting the data ingestion component")
            data_ingestion = DataIngestion(data_ingestion_config=self.data_ingestion_config)
            data_ingestion_artifact = data_ingestion.initiate_data_ingestion()
            logger.info(f"Data Ingestion stage completed and artifact:\n{data_ingestion_artifact}")
            return data_ingestion_artifact

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def start_data_validation(
        self,
        data_ingestion_artifact: DataIngestionArtifact
    ) -> DataValidationArtifact:
        """Initiate data validation component"""
        try:
            data_validation_config = DataValidationConfig(training_pipeline_config=self.training_pipeline_config)
            data_validation = DataValidation(
                data_ingestion_artifact=data_ingestion_artifact,
                data_validation_config=data_validation_config
            )
            logger.info("Initiate data validation component")
            data_valdiation_artifact = data_validation.initiate_data_validation()
            logger.info(f"Completed data validation stage and artifact: {data_valdiation_artifact}")
            return data_valdiation_artifact
        
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def start_data_transformation(
        self, 
        data_validation_artifact: DataValidationArtifact
    ) -> DataTransformationArtifact:
        """Initiate the data transformation compoent"""
        try:
            data_transformation_config = DataTransformationConfig(training_pipeline_config=self.training_pipeline_config)
            data_transformation = DataTransformation(
                data_validation_artifact=data_validation_artifact,
                data_transformation_config=data_transformation_config
            )
            logger.info(f"Initiating the data transformation component")
            data_transformation_artifact = data_transformation.initiate_data_transformation()
            logger.info(f"Completed Data Transformation component and artifact:\n{data_transformation_artifact}")
            return data_transformation_artifact
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def start_model_trainer(
        self,
        data_transformation_artifact: DataTransformationArtifact
    ) -> ModelTrainerArtifact:
        """Initiate the ModelTrainer Component"""
        try:
            model_trainer_config = ModelTrainerConfig(training_pipeline_config=self.training_pipeline_config)
            model_trainer = ModelTrainer(
                model_trainer_config=model_trainer_config,
                data_transformation_artifact=data_transformation_artifact    
            )
            logger.info("Initiate the ModelTrainer component")
            model_trainer_artifact = model_trainer.initiate_model_trainer()
            logger.info(f"Completed model traine stage and artifact:\n{model_trainer_artifact}")
            return model_trainer_artifact
        
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def sync_artifact_dir_to_s3(self):
        """Push artifacts folder to the aws s3 bucket"""
        try:
            self.s3_sync.sync_folder_to_s3(
                folder=self.training_pipeline_config.artifact_dir,
                bucket=settings.training_bucket_name,
                prefix=f"artifact/{self.training_pipeline_config.timestamp}"
            )

        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def sync_saved_model_dir_to_s3(self):
        """Push trained model to aws s3 bucket"""
        try:
            self.s3_sync.sync_folder_to_s3(
                folder=self.training_pipeline_config.model_dir,
                bucket=settings.training_bucket_name,
                prefix=f"final_model/{self.training_pipeline_config.timestamp}"
            )
        except Exception as e:
            raise NetworkSecurityException(e,sys)

    def run_pipeline(self):
        """Run all the pipeline stages"""
        try:
            data_ingestion_artifact = self.start_data_ingestion()
            
            data_validation_artifact = self.start_data_validation(
                data_ingestion_artifact=data_ingestion_artifact
            )
            
            data_transformation_artifact = self.start_data_transformation(
                data_validation_artifact=data_validation_artifact
            )
            
            model_trainer_artifact = self.start_model_trainer(
                data_transformation_artifact=data_transformation_artifact
            )

            self.sync_artifact_dir_to_s3()
            self.sync_saved_model_dir_to_s3()

            return model_trainer_artifact
        except Exception as e:
            raise NetworkSecurityException(e, sys)
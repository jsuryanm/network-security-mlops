from datetime import datetime 
from pathlib import Path 

from pydantic import (
    BaseModel,
    Field,
    ConfigDict
)

from app.constants import training_pipeline


class TrainingPipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True) # makes the class immutable
    timestamp: str = Field(datetime.now().strftime("%m_%d_%Y_%H_%M_%S"))
    pipeline_name: str = training_pipeline.PIPELINE_NAME
    artifact_name: str = training_pipeline.ARTIFACT_DIR
    model_dir: Path = Path("final_model")

    @property
    def artifact_dir(self) -> Path:
        return Path(self.artifact_name) / self.timestamp

    

class DataIngestionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    training_pipeline_config: TrainingPipelineConfig = Field(
        default_factory=TrainingPipelineConfig,
        exclude=True # leaves out field when converting model to JSON
    )

    train_test_split_ratio: float = Field(
        default=training_pipeline.DATA_INGESTION_TRAIN_TEST_SPLIT_RATIO,
        gt=0,
        le=1
    )

    collection_name: str = training_pipeline.DATA_INGESTION_COLLECTION_NAME
    database_name: str = training_pipeline.DATA_INGESTION_DATABASE_NAME

    @property
    def data_ingestion_dir(self) -> Path:
        return (
            self.training_pipeline_config.artifact_dir /
            training_pipeline.DATA_INGESTION_DIR_NAME
        )

    @property
    def feature_store_file_path(self) -> Path:
        return (
            self.data_ingestion_dir / 
            training_pipeline.DATA_INGESTION_FEATURE_STORE_DIR / 
            training_pipeline.FILE_NAME
        )

    @property
    def training_file_path(self) -> Path:
        return (
            self.data_ingestion_dir / 
            training_pipeline.DATA_INGESTION_INGESTED_DIR / 
            training_pipeline.TRAIN_FILE_NAME
        )

    @property
    def testing_file_path(self) -> Path:
        return (
            self.data_ingestion_dir / 
            training_pipeline.DATA_INGESTION_INGESTED_DIR / 
            training_pipeline.TEST_FILE_NAME
        )

class DataValidationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    training_pipeline_config: TrainingPipelineConfig = Field(
        default_factory=TrainingPipelineConfig,
        exclude=True # leaves out field when converting model to JSON
    )

    @property
    def data_validation_dir(self) -> Path:
        return (
            self.training_pipeline_config.artifact_dir /
            training_pipeline.DATA_VALIDATION_DIR_NAME
        )

    @property
    def valid_data_dir(self) -> Path:
        return (
            self.data_validation_dir / 
            training_pipeline.DATA_VALIDATION_VALID_DIR
        )

    @property 
    def invalid_data_dir(self) -> Path:
        return (
            self.data_validation_dir / 
            training_pipeline.DATA_VALIDATION_INVALID_DIR
        )

    @property
    def valid_train_file_path(self) -> Path:
        return (
            self.valid_data_dir / 
            training_pipeline.TRAIN_FILE_NAME
        )

    @property
    def valid_test_file_path(self) -> Path:
        return (
            self.valid_data_dir / 
            training_pipeline.TEST_FILE_NAME
        )

    @property
    def invalid_train_file_path(self) -> Path:
        return (
            self.invalid_data_dir / 
            training_pipeline.TRAIN_FILE_NAME
        )

    @property
    def invalid_test_file_path(self) -> Path:
        return (
            self.invalid_data_dir / 
            training_pipeline.TEST_FILE_NAME
        )

    @property
    def drift_report_file_path(self) -> Path:
        return (
            self.data_validation_dir / 
            training_pipeline.DATA_VALIDATION_DRIFT_REPORT_DIR / 
            training_pipeline.DATA_VALIDATION_DRIFT_REPORT_FILE_NAME
        )

    @property
    def drift_html_report_file_path(self) -> Path:
        return (
            self.data_validation_dir / 
            training_pipeline.DATA_VALIDATION_DRIFT_REPORT_DIR / 
            training_pipeline.DATA_VALIDATION_DRIFT_HTML_FILE_NAME
        )

class DataTransformationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    training_pipeline_config: TrainingPipelineConfig = Field(
        default_factory=TrainingPipelineConfig,
        exclude=True # leaves out field when converting model to JSON
    )
    
    @property
    def data_transformation_dir(self) -> Path:
        return (
            self.training_pipeline_config.artifact_dir /
            training_pipeline.DATA_TRANSFORMATION_DIR_NAME
        )

    @property
    def transformed_train_file_path(self) -> Path:
        return (
            self.data_transformation_dir /
            training_pipeline.DATA_TRANSFORMATION_TRANSFORMED_DATA_DIR / 
            training_pipeline.TRAIN_FILE_NAME.replace("csv","npy")
        )

    @property
    def transformed_test_file_path(self) -> Path:
        return (
            self.data_transformation_dir /
            training_pipeline.DATA_TRANSFORMATION_TRANSFORMED_DATA_DIR / 
            training_pipeline.TEST_FILE_NAME.replace("csv","npy")
        )

    @property
    def transformed_object_file_path(self) -> Path:
        return (
            self.data_transformation_dir / 
            training_pipeline.DATA_TRANSFORMATION_TRANSFORMED_OBJECT_DIR /
            training_pipeline.PREPROCESSING_OBJECT_FILE_NAME
        )


class ModelTrainerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    training_pipeline_config: TrainingPipelineConfig = Field(
        default_factory=TrainingPipelineConfig,
        exclude=True # leaves out field when converting model to JSON
    )

    @property
    def model_trainer_dir(self) -> Path:
        return (
            self.model_trainer_dir /
            training_pipeline.MODEL_TRAINER_DIR_NAME
        )

    @property
    def trained_model_file_path(self) -> Path:
        return (
            self.model_trainer_dir / 
            training_pipeline.MODEL_TRAINER_DIR_NAME /
            training_pipeline.MODEL_TRAINER_TRAINED_MODEL_DIR /
            training_pipeline.MODEL_TRAINER_TRAINED_MODEL_NAME
        )

    expected_accuracy: float = Field(
        default=training_pipeline.MODEL_TRAINER_EXPECTED_SCORE,
        le=1.0,
        ge=0
    )

    overfitting_underfitting_threshold: float = Field(
        default=training_pipeline.MODEL_TRAINER_OVER_FIITING_UNDER_FITTING_THRESHOLD,
        le=1.0,
        ge=0.0
    )
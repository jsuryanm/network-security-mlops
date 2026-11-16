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

    
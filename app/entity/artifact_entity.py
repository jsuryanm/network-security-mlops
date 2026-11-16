from pydantic import BaseModel
from pathlib import Path


class DataIngestionArtifact(BaseModel):
    trained_file_path: Path
    test_file_path: Path


class DataValidationArtifact(BaseModel):
    validation_status: bool 
    valid_train_file_path: Path 
    valid_test_file_path: Path 
    invalid_train_file_path: Path 
    invalid_test_file_path: Path
    drift_report_file_path: Path 
        
from pydantic import BaseModel
from pathlib import Path
from typing import Optional


class DataIngestionArtifact(BaseModel):
    trained_file_path: Path
    test_file_path: Path


class DataValidationArtifact(BaseModel):
    validation_status: bool
    valid_train_file_path: Optional[Path] = None
    valid_test_file_path: Optional[Path] = None
    invalid_train_file_path: Optional[Path] = None
    invalid_test_file_path: Optional[Path] = None
    drift_report_file_path: Path
    drift_html_report_file_path: Path
    drifted_columns: list[str] = []

class DataTranformationArtifact(BaseModel):
    transformed_object_file_path: str 
    transformed_train_file_path: str
    transformed_test_file_path: str 
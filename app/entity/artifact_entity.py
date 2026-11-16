from pydantic import BaseModel
from pathlib import Path


class DataIngestionArtifact(BaseModel):
    trained_file_path: Path
    test_file_path: Path
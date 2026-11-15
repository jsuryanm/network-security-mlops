from datetime import datetime 
from pathlib import Path 

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator
)

from app.constants import training_pipeline


class TrainingPipelineConfig(BaseModel):
    def __init__(self, name, bases, dict, /, **kwds):
        super().__init__(name, bases, dict, **kwds)

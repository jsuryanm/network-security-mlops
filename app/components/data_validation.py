from app.core.config import get_settings
from app.entity.config_entity import DataValidationConfig

from app.entity.artifact_entity import (
    DataIngestionArtifact,
    DataValidationArtifact
)

from scipy.stats import ks_2samp

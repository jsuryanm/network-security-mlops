from pathlib import Path

import pytest
from pydantic import ValidationError

from app.entity.config_entity import (
    DataIngestionConfig,
    DataValidationConfig,
    TrainingPipelineConfig,
)


@pytest.fixture
def pipeline_config():
    return TrainingPipelineConfig(timestamp="01_01_2027_00_00_00")


def test_artifact_dir_uses_timestamp(pipeline_config):
    assert pipeline_config.artifact_dir == Path("Artifacts") / "01_01_2027_00_00_00"


def test_model_dir_matches_where_trainer_saves():
    """The trainer writes to final_models/; the S3 upload reads this config value."""
    assert TrainingPipelineConfig().model_dir == Path("final_models")


def test_stage_paths_live_under_the_run_folder(pipeline_config):
    ingestion = DataIngestionConfig(training_pipeline_config=pipeline_config)
    validation = DataValidationConfig(training_pipeline_config=pipeline_config)
    run_dir = pipeline_config.artifact_dir
    assert run_dir in ingestion.training_file_path.parents
    assert run_dir in ingestion.testing_file_path.parents
    assert run_dir in validation.drift_report_file_path.parents


@pytest.mark.parametrize("ratio", [0, -0.1, 1.5])
def test_bad_split_ratio_rejected(ratio, pipeline_config):
    with pytest.raises(ValidationError):
        DataIngestionConfig(
            training_pipeline_config=pipeline_config, train_test_split_ratio=ratio
        )


def test_configs_are_immutable(pipeline_config):
    with pytest.raises(ValidationError):
        pipeline_config.timestamp = "changed"

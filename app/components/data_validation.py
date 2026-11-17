import sys
from pathlib import Path

import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.presets import DataDriftPreset

from app.logging.logger import logger
from app.exception.exceptions import NetworkSecurityException
from app.constants.training_pipeline import (
    SCHEMA_FILE_PATH,
    DATA_DRIFT_METHOD,
    DATA_DRIFT_THRESHOLD,
    DATA_DRIFT_SHARE,
    DATA_DRIFT_CRITICAL_COLUMNS,
)

from app.entity.config_entity import DataValidationConfig
from app.entity.artifact_entity import (
    DataIngestionArtifact,
    DataValidationArtifact
)
from app.utils.main_utils.utils import (
    read_yaml_file,
    write_yaml_file
)


class DataValidation:
    def __init__(
        self,
        data_ingestion_artifact: DataIngestionArtifact,
        data_validation_config: DataValidationConfig,
    ):
        try:
            self.data_ingestion_artifact = data_ingestion_artifact
            self.data_validation_config = data_validation_config
            self._schema_config = read_yaml_file(SCHEMA_FILE_PATH)

        except Exception as e:
            raise NetworkSecurityException(e, sys) from e

    @staticmethod
    def read_data(file_path: Path) -> pd.DataFrame:
        """Reads a csv file into a dataframe"""
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise NetworkSecurityException(e, sys) from e

    def validate_num_columns(self, dataframe: pd.DataFrame) -> bool:
        """True if the dataframe has as many columns as the schema defines"""
        try:
            required = len(self._schema_config["columns"])
            actual = len(dataframe.columns)
            logger.info(f"Required number of columns: {required} | dataframe has: {actual}")
            return required == actual
        except Exception as e:
            raise NetworkSecurityException(e, sys) from e

    def detect_data_drift(
        self,
        base_df: pd.DataFrame,
        current_df: pd.DataFrame,
    ) -> bool:
        """Compare `current_df` against `base_df` with Evidently.

        Writes an HTML report and a YAML summary. Returns True when drift is detected,
        i.e. a critical column drifted or the share of drifted columns is too high.
        """
        try:
            # Features are -1/0/1 codes (not magnitudes), so treat every column as categorical
            definition = DataDefinition(categorical_columns=list(base_df.columns)) 
            # schema map that tells evidently what each col in dataset represents
            
            reference = Dataset.from_pandas(base_df, data_definition=definition)
            current = Dataset.from_pandas(current_df, data_definition=definition)

            # Method is fixed on purpose: Evidently's default switches test (and the meaning
            # of the threshold) depending on row count.
            report = Report([DataDriftPreset(
                cat_method=DATA_DRIFT_METHOD,
                cat_threshold=DATA_DRIFT_THRESHOLD,
                drift_share=DATA_DRIFT_SHARE,
            )])
            snapshot = report.run(current, reference)  # order: current first, reference second

            column_report = self._column_drift_report(snapshot)
            drifted = [c for c, r in column_report.items() if r["drift_status"]]
            share = len(drifted) / len(column_report)
            critical = [c for c in drifted if c in DATA_DRIFT_CRITICAL_COLUMNS]
            drift_detected = bool(critical) or share >= DATA_DRIFT_SHARE

            html_path = Path(self.data_validation_config.drift_html_report_file_path)
            html_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot.save_html(str(html_path))

            write_yaml_file(
                file_path=self.data_validation_config.drift_report_file_path,
                content={
                    "summary": {
                        "drift_detected": drift_detected,
                        "drifted_columns": drifted,
                        "drifted_critical_columns": critical,
                        "drift_share": round(share, 4),
                        "method": DATA_DRIFT_METHOD,
                        "threshold": DATA_DRIFT_THRESHOLD,
                    },
                    "columns": column_report,
                },
            )

            logger.info(
                f"Data drift detected={drift_detected} | drifted={drifted} | "
                f"share={share:.2%} | critical={critical}"
            )
            return drift_detected

        except Exception as e:
            logger.exception("Data drift detection failed")
            raise NetworkSecurityException(e, sys) from e

    @staticmethod
    def _column_drift_report(snapshot) -> dict[str, dict]:
        """Per-column {distance, threshold, drift_status} from an Evidently snapshot"""
        result = {}
        for metric in snapshot.dict()["metrics"]:
            cfg = metric["config"]
            if cfg["type"].endswith("ValueDrift"):
                distance = float(metric["value"])
                result[cfg["column"]] = {
                    "distance": distance,
                    "threshold": cfg["threshold"],
                    "drift_status": distance >= cfg["threshold"],  # distance test: >= means drift
                }
        return result

    def initiate_data_validation(self) -> DataValidationArtifact:
        """Validate columns and data drift, then save train/test as valid or invalid"""
        try:
            config = self.data_validation_config
            train_dataframe = DataValidation.read_data(self.data_ingestion_artifact.trained_file_path)
            test_dataframe = DataValidation.read_data(self.data_ingestion_artifact.test_file_path)

            columns_ok = True
            if not self.validate_num_columns(train_dataframe):
                logger.error("Train dataframe does not contain all the columns")
                columns_ok = False
            if not self.validate_num_columns(test_dataframe):
                logger.error("Test dataframe does not contain all the columns")
                columns_ok = False

            # drift needs the same columns in both frames, so only run it on a valid schema
            drift_detected = (
                self.detect_data_drift(base_df=train_dataframe, current_df=test_dataframe)
                if columns_ok else False
            )
            status = columns_ok and not drift_detected

            if status:
                train_path, test_path = config.valid_train_file_path, config.valid_test_file_path
            else:
                train_path, test_path = config.invalid_train_file_path, config.invalid_test_file_path

            Path(train_path).parent.mkdir(parents=True, exist_ok=True)
            train_dataframe.to_csv(train_path, index=False, header=True)
            test_dataframe.to_csv(test_path, index=False, header=True)

            drifted_columns = []
            if columns_ok:
                report = read_yaml_file(config.drift_report_file_path)
                drifted_columns = report["summary"]["drifted_columns"]

            logger.info(f"Data validation status={status} | files saved to {Path(train_path).parent}")

            return DataValidationArtifact(
                validation_status=status,
                valid_train_file_path=train_path if status else None,
                valid_test_file_path=test_path if status else None,
                invalid_train_file_path=None if status else train_path,
                invalid_test_file_path=None if status else test_path,
                drift_report_file_path=config.drift_report_file_path,
                drift_html_report_file_path=config.drift_html_report_file_path,
                drifted_columns=drifted_columns,
            )

        except Exception as e:
            logger.exception("Data validation failed")
            raise NetworkSecurityException(e, sys) from e

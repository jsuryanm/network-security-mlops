from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


_PHISHING_EXAMPLE = {"having_IP_Address": -1, "URL_Length": 1, "Shortining_Service": 1, "having_At_Symbol": 1, "double_slash_redirecting": -1, "Prefix_Suffix": -1, "having_Sub_Domain": -1, "SSLfinal_State": -1, "Domain_registeration_length": -1, "Favicon": 1, "port": 1, "HTTPS_token": -1, "Request_URL": 1, "URL_of_Anchor": -1, "Links_in_tags": 1, "SFH": -1, "Submitting_to_email": -1, "Abnormal_URL": -1, "Redirect": 0, "on_mouseover": 1, "RightClick": 1, "popUpWidnow": 1, "Iframe": 1, "age_of_domain": -1, "DNSRecord": -1, "web_traffic": -1, "Page_Rank": -1, "Google_Index": 1, "Links_pointing_to_page": 1, "Statistical_report": -1}
_LEGIT_EXAMPLE = {"having_IP_Address": 1, "URL_Length": 0, "Shortining_Service": -1, "having_At_Symbol": 1, "double_slash_redirecting": 1, "Prefix_Suffix": -1, "having_Sub_Domain": 1, "SSLfinal_State": 1, "Domain_registeration_length": -1, "Favicon": 1, "port": 1, "HTTPS_token": 1, "Request_URL": 1, "URL_of_Anchor": 0, "Links_in_tags": 0, "SFH": -1, "Submitting_to_email": 1, "Abnormal_URL": 1, "Redirect": 0, "on_mouseover": -1, "RightClick": 1, "popUpWidnow": -1, "Iframe": 1, "age_of_domain": -1, "DNSRecord": -1, "web_traffic": 0, "Page_Rank": -1, "Google_Index": 1, "Links_pointing_to_page": 1, "Statistical_report": 1}


class PredictRequest(BaseModel):
    # Swagger "Try it out" prefills this: one known phishing row, one known legitimate row.
    model_config = ConfigDict(json_schema_extra={"example": {"records": [_PHISHING_EXAMPLE, _LEGIT_EXAMPLE]}})

    records: list[dict[str, int]] = Field(min_length=1, max_length=1000)


class Prediction(BaseModel):
    prediction: int
    label: Literal["legitimate", "phishing"]


class PredictResponse(BaseModel):
    predictions: list[Prediction]


class PredictionPage(BaseModel):
    total: int
    items: list[dict]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    mongodb: bool
    mlflow: bool


class TrainingStatus(BaseModel):
    status: Literal["idle", "running", "succeeded", "failed"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    test_f1_score: float | None = None

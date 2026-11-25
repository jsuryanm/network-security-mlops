from pydantic import Field 
from pydantic_settings import SettingsConfigDict, BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # mongodb credentials 
    mongodb_username: str = Field(default=str)
    mongodb_password: str = Field(default=str)
    mongodb_uri: str = Field(default=str)

    mlflow_uri: str = Field(default=str)
    
    # dagshub
    dagshub_repo_owner: str = Field(default=str)
    dagshub_repo_name: str = Field(default=str)

    # aws s3 bucket name
    training_bucket_name: str = Field(default=str)
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns the Settings object"""
    return Settings()

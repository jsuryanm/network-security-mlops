from pydantic import Field 
from pydantic_settings import SettingsConfigDict, BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # mongodb credentials 
    mongodb_username: str = Field(default=str)
    mongodb_password: str = Field(default=str)
    mongodb_uri: str = Field(default=str)
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns the Settings object"""
    return Settings()

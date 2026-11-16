import yaml
import joblib 
import os 
import sys 
from pathlib import Path 
import numpy as np 
import joblib

from app.exception.exceptions import NetworkSecurityException
from app.logging.logger import logger 

def read_yaml_file(file_path: Path) -> dict:
    try: 
        with open(file_path, 'rb') as yaml_file: 
            return yaml.safe_load(yaml_file)
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def write_yaml_file(
    file_path: Path,
    content: object,
    replace: bool = False,
) -> None:
    try:
        if replace:
            if Path(file_path).exists():
                Path(file_path).unlink()
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as file:
                yaml.dump(content, file)
                
    except Exception as e:
        raise NetworkSecurityException(e, sys)
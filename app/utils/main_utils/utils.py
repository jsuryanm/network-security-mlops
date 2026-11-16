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
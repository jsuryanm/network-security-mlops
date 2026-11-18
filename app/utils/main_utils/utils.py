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
    replace: bool = True,
) -> None:
    """Write `content` as YAML. Creates parent dirs; overwrites when replace=True."""
    try:
        file_path = Path(file_path)
        if file_path.exists() and not replace:
            return
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as file:
            yaml.dump(content, file)

    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def save_numpy_array_data(file_path: Path, array: np.array):
    """Save numpy array data to file
    file_path: str location of the file, 
    array: np.array to save"""
    try:
        dir_path = Path(file_path).parent
        os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'wb') as file_obj:
            np.save(file_obj, array)
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e

def save_object(file_path: Path, obj: object) -> None:
    try:
        os.makedirs(os.path.dirname(file_path),exist_ok=True)
        with open(file_path, 'wb') as file_obj:
            joblib.dump(obj,file_obj)
    
    except Exception as e:
        raise NetworkSecurityException(e, sys) from e 
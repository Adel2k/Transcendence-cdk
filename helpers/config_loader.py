import os
import yaml

def load_yaml_config(path: str) -> dict:
    full_path = os.path.join(os.path.dirname(__file__), '..', path)
    with open(full_path, 'r') as f:
        return yaml.safe_load(f)

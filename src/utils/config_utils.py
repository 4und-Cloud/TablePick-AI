import yaml
from src.utils.path_utils import get_project_root

def load_config():
    project_root = get_project_root()
    config_path = project_root / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
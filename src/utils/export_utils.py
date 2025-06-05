import subprocess
import os
from src.utils.path_utils import get_project_root
from src.utils.config_utils import load_config

def run_export_scripts():
    try:
        config = load_config()
        project_root = get_project_root()
        venv_python = project_root / (
            config["venv_python"]["windows"] if os.name == "nt"
            else config["venv_python"]["linux"]
        )
        export_scripts = [
            project_root / script for script in config["export_scripts"]
        ]
        for script in export_scripts:
            print(f"Running {script} ...")
            subprocess.run([str(venv_python), str(script)], check=True)
    except Exception as e:
        print(f"Error running export scripts: {e}")
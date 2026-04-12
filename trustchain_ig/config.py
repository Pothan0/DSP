import yaml
from pathlib import Path

def load_config(config_path="secfai/config.yaml"):
    path = Path(config_path)
    if not path.exists():
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

if __name__ == "__main__":
    config = load_config()
    print("Loaded config:", config)

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Configuration manager for loading and managing Prediction configs.
    """

    def __init__(self, config_dir: str | Path | None = None):
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = Path(config_dir)

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Load configuration from YAML or JSON file

        Args:
            config_name: Name of config file (with or without extension)

        Returns:
            Dictionary containing configuration
        """
        config_path = self._find_config_file(config_name)

        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            return self._load_yaml(config_path)
        elif config_path.suffix.lower() == '.json':
            return self._load_json(config_path)
        else:
            raise ValueError(f"Unsupported config format: {config_path.suffix}")

    def _find_config_file(self, config_name: str) -> Path:
        """Find config file with various extensions"""
        if not config_name.endswith(('.yaml', '.yml', '.json')):
            # Try different extensions
            for ext in ['.yaml', '.yml', '.json']:
                config_path = self.config_dir / f"{config_name}{ext}"
                if config_path.exists():
                    return config_path
            raise FileNotFoundError(f"Config file {config_name} not found in {self.config_dir}")
        else:
            config_path = self.config_dir / config_name
            if not config_path.exists():
                raise FileNotFoundError(f"Config file {config_path} not found")
            return config_path

    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """Load YAML configuration"""
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def _load_json(self, config_path: Path) -> Dict[str, Any]:
        """Load JSON configuration"""
        with open(config_path, 'r') as file:
            return json.load(file)

    def save_config(self, config: Dict[str, Any], config_name: str, format: str = 'yaml'):
        """
        Save configuration to file

        Args:
            config: Configuration dictionary
            config_name: Name of config file
            format: Format to save ('yaml' or 'json')
        """
        if format.lower() == 'yaml':
            config_path = self.config_dir / f"{config_name}.yaml"
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False)
        elif format.lower() == 'json':
            config_path = self.config_dir / f"{config_name}.json"
            with open(config_path, 'w') as file:
                json.dump(config, file, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global config manager instance
config_manager = ConfigManager()

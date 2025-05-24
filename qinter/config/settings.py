"""
qinter/config/settings.py
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class RegistryConfig:
    """Configuration for package registries."""
    name: str
    url: str
    priority: int = 1
    enabled: bool = True


@dataclass
class QinterSettings:
    """Main Qinter configuration."""
    # Package management
    auto_update: bool = False
    cache_duration_days: int = 7
    max_pack_size_mb: int = 10
    
    # Display preferences
    max_suggestions: int = 5
    max_examples: int = 3
    show_pack_info: bool = False
    color_theme: str = "default"
    
    # Behavior
    auto_activate: bool = False
    fallback_to_original: bool = True
    debug_mode: bool = False
    
    # Registry configuration
    registry_url: str = "http://127.0.0.1:8000"  # Default to local backend
    
    # Registries
    registries: List[RegistryConfig] = None
    
    def __post_init__(self):
        if self.registries is None:
            self.registries = [
                RegistryConfig(
                    name="local",
                    url=self.registry_url,
                    priority=1
                ),
                RegistryConfig(
                    name="official",
                    url="https://registry.qinter.dev",
                    priority=2
                )
            ]


class SettingsManager:
    """Manages Qinter configuration and settings."""
    
    def __init__(self):
        self._settings: Optional[QinterSettings] = None
        self._config_file = self._get_config_file_path()
    
    def get_settings(self) -> QinterSettings:
        """Get current settings, loading from file if needed."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def save_settings(self, settings: QinterSettings) -> bool:
        """Save settings to file."""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            
            settings_dict = asdict(settings)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings_dict, f, default_flow_style=False, sort_keys=False)
            
            self._settings = settings
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to save settings: {e}")
            return False
    
    def update_registry_url(self, url: str) -> bool:
        """Update the registry URL."""
        settings = self.get_settings()
        settings.registry_url = url
        
        # Update the local registry in the list
        for registry in settings.registries:
            if registry.name == "local":
                registry.url = url
                break
        
        return self.save_settings(settings)
    
    def _load_settings(self) -> QinterSettings:
        """Load settings from file or create defaults."""
        if not self._config_file.exists():
            default_settings = QinterSettings()
            self.save_settings(default_settings)
            return default_settings
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                settings_dict = yaml.safe_load(f)
            
            # Convert registries list to RegistryConfig objects
            if 'registries' in settings_dict:
                registries = []
                for reg_dict in settings_dict['registries']:
                    registries.append(RegistryConfig(**reg_dict))
                settings_dict['registries'] = registries
            
            return QinterSettings(**settings_dict)
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to load settings, using defaults: {e}")
            return QinterSettings()
    
    def _get_config_file_path(self) -> Path:
        """Get the path to the configuration file."""
        return Path.home() / ".qinter" / "config.yaml"


# Global settings manager
_settings_manager = SettingsManager()

def get_settings() -> QinterSettings:
    """Get current Qinter settings."""
    return _settings_manager.get_settings()

def get_settings_manager() -> SettingsManager:
    """Get the settings manager instance."""
    return _settings_manager
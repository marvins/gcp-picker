#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2026 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    config_manager.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Configuration Manager - Load and manage application configuration
"""

#  Python Standard Libraries
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Imagery_Service:
    """Imagery service configuration."""
    name: str
    url: str
    type: str
    attribution: str
    description: str = ""
    max_zoom: int = 19
    enabled: bool = True
    priority: int = 10
    layers: str = ""
    format: str = "image/png"
    note: str = ""


@dataclass
class Map_Settings:
    """Map configuration settings."""
    default_center: Dict[str, float]
    default_zoom: int
    min_zoom: int
    max_zoom: int
    default_service: str = "Esri World Imagery"


@dataclass
class Application_Settings:
    """Application-wide settings."""
    auto_fetch_elevation: bool
    elevation_service: str
    show_gcp_ids: bool
    default_point_size: int
    coordinate_format: str
    precision: Dict[str, int]


class Config_Manager:
    """Manages application configuration from JSON files."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            # Default to data/config relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "data" / "config"

        self.config_dir = config_dir
        self.imagery_services_config = {}
        self.map_settings = None
        self.application_settings = None
        self.default_service = None  # Will be loaded from config

        self.load_config()

    def load_config(self):
        """Load configuration from JSON files."""
        # Load imagery services configuration
        imagery_config_path = self.config_dir / "imagery_services.json"
        if imagery_config_path.exists():
            with open(imagery_config_path, 'r') as f:
                config = json.load(f)
                self._parse_imagery_services(config.get("imagery_services", {}))
                self._parse_map_settings(config.get("map_settings", {}))
                self._parse_application_settings(config.get("application_settings", {}))
        else:
            # Fallback to hardcoded services if config file doesn't exist
            self._load_fallback_config()

    def _parse_imagery_services(self, services_config: Dict[str, Any]):
        """Parse imagery services from configuration."""
        self.imagery_services_config = {}
        for service_id, service_data in services_config.items():
            self.imagery_services_config[service_id] = Imagery_Service(**service_data)

    def _parse_map_settings(self, map_config: Dict[str, Any]):
        """Parse map settings from configuration."""
        if map_config:
            self.map_settings = Map_Settings(**map_config)

    def _parse_application_settings(self, app_config: Dict[str, Any]):
        """Parse application settings from configuration."""
        if app_config:
            self.application_settings = Application_Settings(**app_config)

    def _load_fallback_config(self):
        """Load fallback configuration when config file is not available."""
        self.imagery_services_config = {
            "OpenStreetMap": Imagery_Service(
                name="OpenStreetMap",
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                type="xyz",
                attribution="© OpenStreetMap contributors",
                description="Open source world map",
                max_zoom=19,
                enabled=True,
                priority=10
            ),
            "Esri World Imagery": Imagery_Service(
                name="Esri World Imagery",
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                type="xyz",
                attribution="© Esri",
                description="Esri global satellite imagery",
                max_zoom=19,
                enabled=True,
                priority=5
            )
        }

        self.map_settings = Map_Settings(
            default_center={"latitude": 39.8283, "longitude": -98.5795},
            default_zoom=4,
            min_zoom=2,
            max_zoom=20
        )

        self.application_settings = Application_Settings(
            auto_fetch_elevation=True,
            elevation_service="google",
            show_gcp_ids=True,
            default_point_size=8,
            coordinate_format="decimal_degrees",
            precision={"latitude": 6, "longitude": 6, "elevation": 1}
        )

    def get_enabled_imagery_services(self) -> List[Imagery_Service]:
        """Get list of enabled imagery services sorted by priority."""
        enabled_services = [
            service for service in self.imagery_services_config.values()
            if service.enabled
        ]
        return sorted(enabled_services, key=lambda x: x.priority)

    def get_imagery_service(self, service_name: str) -> Imagery_Service | None:
        """Get a specific imagery service by name."""
        for service in self.imagery_services_config.values():
            if service.name == service_name:
                return service
        return None

    def get_imagery_services_dict(self) -> Dict[str, Dict[str, Any]]:
        """Get imagery services as a dictionary for UI components."""
        services_dict = {}
        for service in self.get_enabled_imagery_services():
            services_dict[service.name] = {
                "url": service.url,
                "type": service.type,
                "attribution": service.attribution,
                "layers": service.layers,
                "format": service.format,
                "max_zoom": service.max_zoom,
                "description": service.description
            }
        return services_dict

    def get_default_service(self) -> str:
        """Get the default imagery service name."""
        # Use default service from map settings if available
        if self.map_settings and hasattr(self.map_settings, 'default_service') and self.map_settings.default_service:
            default_service_name = self.map_settings.default_service
        elif self.default_service:  # Fallback to legacy default_service
            default_service_name = self.default_service
        else:
            default_service_name = "NAIP CONUS (ArcGIS)"  # Ultimate fallback

        # Check if default service is enabled
        default_service = self.get_imagery_service(default_service_name)
        if default_service and default_service.enabled:
            return default_service_name

        # Fallback to first enabled service
        enabled_services = self.get_enabled_imagery_services()
        if enabled_services:
            return enabled_services[0].name

        # Last resort
        return "OpenStreetMap"

    def get_map_settings(self) -> Map_Settings:
        """Get map configuration settings."""
        return self.map_settings

    def get_application_settings(self) -> Application_Settings:
        """Get application-wide settings."""
        return self.application_settings

    def save_config(self):
        """Save current configuration to file."""
        config = {
            "imagery_services": {
                service_id: {
                    "name": service.name,
                    "url": service.url,
                    "type": service.type,
                    "attribution": service.attribution,
                    "description": service.description,
                    "max_zoom": service.max_zoom,
                    "enabled": service.enabled,
                    "priority": service.priority,
                    "layers": service.layers,
                    "format": service.format,
                    "note": service.note
                }
                for service_id, service in self.imagery_services_config.items()
            },
            "map_settings": {
                "default_center": self.map_settings.default_center,
                "default_zoom": self.map_settings.default_zoom,
                "min_zoom": self.map_settings.min_zoom,
                "max_zoom": self.map_settings.max_zoom,
                "default_service": self.map_settings.default_service
            },
            "application_settings": {
                "auto_fetch_elevation": self.application_settings.auto_fetch_elevation,
                "elevation_service": self.application_settings.elevation_service,
                "show_gcp_ids": self.application_settings.show_gcp_ids,
                "default_point_size": self.application_settings.default_point_size,
                "coordinate_format": self.application_settings.coordinate_format,
                "precision": self.application_settings.precision
            }
        }

        config_path = self.config_dir / "imagery_services.json"
        os.makedirs(self.config_dir, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def reload_config(self):
        """Reload configuration from files."""
        self.load_config()


# Global config manager instance
_config_manager = None

def get_config_manager() -> Config_Manager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = Config_Manager()
    return _config_manager

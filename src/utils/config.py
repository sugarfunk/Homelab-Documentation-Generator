"""Configuration management."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class SSHConfigModel(BaseModel):
    """SSH configuration."""
    user: str
    key_path: Optional[str] = None
    password: Optional[str] = None
    port: int = 22


class ServerConfigModel(BaseModel):
    """Server configuration."""
    name: str
    hostname: str
    tailscale_ip: Optional[str] = None
    local_ip: Optional[str] = None
    public_ip: Optional[str] = None
    ssh: Optional[SSHConfigModel] = None
    role: str = "utility_server"
    criticality: str = "nice-to-have"


class TailscaleConfigModel(BaseModel):
    """Tailscale configuration."""
    enabled: bool = True
    api_key: Optional[str] = None
    tailnet: Optional[str] = None


class ReverseProxyConfigModel(BaseModel):
    """Reverse proxy configuration."""
    name: str
    server: str
    type: str = "traefik"
    config_path: str


class InfrastructureConfigModel(BaseModel):
    """Infrastructure configuration."""
    servers: List[ServerConfigModel] = Field(default_factory=list)
    tailscale: Optional[TailscaleConfigModel] = None
    docker_compose_paths: List[str] = Field(default_factory=list)
    reverse_proxies: List[ReverseProxyConfigModel] = Field(default_factory=list)


class LLMProviderConfigModel(BaseModel):
    """LLM provider configuration."""
    api_key: Optional[str] = None
    model: str
    max_tokens: int = 4096
    base_url: Optional[str] = None


class LLMFeaturesConfigModel(BaseModel):
    """LLM features configuration."""
    service_explanations: bool = True
    troubleshooting_guides: bool = True
    procedure_generation: bool = True
    non_technical_mode: bool = True
    glossary_generation: bool = True


class LLMConfigModel(BaseModel):
    """LLM configuration."""
    default_provider: str = "claude"
    privacy_mode: bool = True
    privacy_provider: str = "ollama"
    providers: Dict[str, LLMProviderConfigModel] = Field(default_factory=dict)
    features: LLMFeaturesConfigModel = Field(default_factory=LLMFeaturesConfigModel)


class ScanningConfigModel(BaseModel):
    """Scanning configuration."""
    schedule: str = "0 2 * * *"
    enabled_scanners: List[str] = Field(default_factory=lambda: ["docker", "server_info"])
    timeouts: Dict[str, int] = Field(default_factory=lambda: {
        "ssh_connection": 30,
        "docker_api": 60,
        "command_execution": 120
    })
    retries: Dict[str, int] = Field(default_factory=lambda: {
        "max_attempts": 3,
        "backoff_multiplier": 2
    })


class DocumentationConfigModel(BaseModel):
    """Documentation generation configuration."""
    output_dir: str = "./output"
    formats: List[str] = Field(default_factory=lambda: ["html", "pdf", "markdown"])
    diagrams: Dict[str, Any] = Field(default_factory=dict)
    theme: str = "default"
    sections: Dict[str, bool] = Field(default_factory=lambda: {
        "server_docs": True,
        "service_docs": True,
        "network_docs": True,
        "procedures": True,
        "emergency_guide": True,
        "glossary": True
    })
    modes: Dict[str, bool] = Field(default_factory=lambda: {
        "technical": True,
        "non_technical": True,
        "emergency": True
    })


class SecurityConfigModel(BaseModel):
    """Security configuration."""
    sanitize_patterns: List[str] = Field(default_factory=lambda: [
        "password", "token", "secret", "key", "api_key", "credential"
    ])
    exclude_services: List[str] = Field(default_factory=list)
    web_auth: Dict[str, Any] = Field(default_factory=dict)
    encryption: Dict[str, Any] = Field(default_factory=dict)


class ChangeDetectionConfigModel(BaseModel):
    """Change detection configuration."""
    enabled: bool = True
    track: List[str] = Field(default_factory=list)
    retention_days: int = 90


class NotificationsConfigModel(BaseModel):
    """Notifications configuration."""
    ntfy: Dict[str, Any] = Field(default_factory=dict)
    triggers: List[str] = Field(default_factory=list)


class EmergencyContactModel(BaseModel):
    """Emergency contact configuration."""
    name: str
    role: str
    phone: Optional[str] = None
    email: Optional[str] = None


class EmergencyConfigModel(BaseModel):
    """Emergency information configuration."""
    password_manager: Dict[str, str] = Field(default_factory=dict)
    backups: List[Dict[str, str]] = Field(default_factory=list)
    contacts: List[EmergencyContactModel] = Field(default_factory=list)
    critical_services: List[str] = Field(default_factory=list)
    business: Optional[Dict[str, Any]] = None


class WebConfigModel(BaseModel):
    """Web interface configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class DatabaseConfigModel(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///./data/homelab_docs.db"


class LoggingConfigModel(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "./data/homelab_docs.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    """Main configuration model."""
    infrastructure: InfrastructureConfigModel = Field(default_factory=InfrastructureConfigModel)
    llm: LLMConfigModel = Field(default_factory=LLMConfigModel)
    scanning: ScanningConfigModel = Field(default_factory=ScanningConfigModel)
    documentation: DocumentationConfigModel = Field(default_factory=DocumentationConfigModel)
    security: SecurityConfigModel = Field(default_factory=SecurityConfigModel)
    change_detection: ChangeDetectionConfigModel = Field(default_factory=ChangeDetectionConfigModel)
    notifications: NotificationsConfigModel = Field(default_factory=NotificationsConfigModel)
    emergency: EmergencyConfigModel = Field(default_factory=EmergencyConfigModel)
    web: WebConfigModel = Field(default_factory=WebConfigModel)
    database: DatabaseConfigModel = Field(default_factory=DatabaseConfigModel)
    logging: LoggingConfigModel = Field(default_factory=LoggingConfigModel)


def expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in configuration."""
    if isinstance(data, dict):
        return {k: expand_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Match ${VAR_NAME} pattern
        pattern = re.compile(r'\$\{([^}]+)\}')
        matches = pattern.findall(data)
        for var_name in matches:
            env_value = os.getenv(var_name, "")
            data = data.replace(f"${{{var_name}}}", env_value)
        return data
    return data


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Config: Loaded configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        # Try config.example.yaml
        example_config = Path("config.example.yaml")
        if example_config.exists():
            print(f"Warning: {config_path} not found, using {example_config}")
            config_file = example_config
        else:
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please copy config.example.yaml to config.yaml and customize it."
            )

    with open(config_file, 'r') as f:
        raw_config = yaml.safe_load(f)

    # Expand environment variables
    expanded_config = expand_env_vars(raw_config)

    # Create and validate config
    try:
        config = Config(**expanded_config)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")

    return config


def get_server_config(config: Config, server_name: str) -> Optional[ServerConfigModel]:
    """Get configuration for a specific server.

    Args:
        config: Main configuration
        server_name: Name of server to find

    Returns:
        ServerConfigModel or None if not found
    """
    for server in config.infrastructure.servers:
        if server.name == server_name:
            return server
    return None

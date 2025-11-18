"""Data models for infrastructure components."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Criticality(str, Enum):
    """Service/server criticality levels."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice-to-have"


class ServerRole(str, Enum):
    """Server role types."""
    PRIMARY = "primary_server"
    SECONDARY = "secondary_server"
    UTILITY = "utility_server"
    MEDIA = "media_server"
    PUBLIC_FACING = "public_facing"
    DEVELOPMENT = "development"
    BACKUP = "backup"


class ServiceStatus(str, Enum):
    """Docker service status."""
    RUNNING = "running"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    PAUSED = "paused"
    DEAD = "dead"
    UNKNOWN = "unknown"


class ResourceUsage(BaseModel):
    """System resource usage metrics."""
    cpu_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    memory_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_percent: float = 0.0
    load_average: Optional[List[float]] = None
    uptime_seconds: Optional[int] = None


class NetworkInterface(BaseModel):
    """Network interface information."""
    name: str
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    is_up: bool = False
    speed_mbps: Optional[int] = None


class SSHConfig(BaseModel):
    """SSH connection configuration."""
    user: str
    key_path: Optional[str] = None
    password: Optional[str] = None
    port: int = 22


class Server(BaseModel):
    """Server/host information."""
    name: str
    hostname: str
    role: ServerRole
    criticality: Criticality

    # Network information
    tailscale_ip: Optional[str] = None
    local_ip: Optional[str] = None
    public_ip: Optional[str] = None
    interfaces: List[NetworkInterface] = Field(default_factory=list)

    # SSH configuration
    ssh: Optional[SSHConfig] = None

    # Hardware information
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    kernel_version: Optional[str] = None
    architecture: Optional[str] = None
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    total_memory_gb: Optional[float] = None

    # Resource usage
    resources: Optional[ResourceUsage] = None

    # Docker information
    docker_version: Optional[str] = None
    docker_compose_version: Optional[str] = None

    # Metadata
    last_scanned: Optional[datetime] = None
    scan_errors: List[str] = Field(default_factory=list)
    reachable: bool = False

    # Custom notes
    notes: Optional[str] = None
    purpose: Optional[str] = None


class DockerVolume(BaseModel):
    """Docker volume information."""
    name: str
    driver: str = "local"
    mount_point: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    size_mb: Optional[float] = None
    created: Optional[datetime] = None


class DockerNetwork(BaseModel):
    """Docker network information."""
    name: str
    driver: str = "bridge"
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    internal: bool = False
    labels: Dict[str, str] = Field(default_factory=dict)


class DockerPort(BaseModel):
    """Docker port mapping."""
    container_port: int
    host_port: Optional[int] = None
    protocol: str = "tcp"
    host_ip: str = "0.0.0.0"


class DockerContainer(BaseModel):
    """Docker container information."""
    id: str
    name: str
    image: str
    status: ServiceStatus
    state: str  # created, running, paused, restarting, removing, exited, dead

    # Configuration
    command: Optional[str] = None
    entrypoint: Optional[str] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)

    # Networking
    ports: List[DockerPort] = Field(default_factory=list)
    networks: List[str] = Field(default_factory=list)
    hostname: Optional[str] = None

    # Storage
    volumes: List[str] = Field(default_factory=list)
    mounts: List[Dict[str, Any]] = Field(default_factory=list)

    # Resource limits
    cpu_limit: Optional[float] = None
    memory_limit_mb: Optional[int] = None

    # Runtime information
    created: Optional[datetime] = None
    started: Optional[datetime] = None
    restart_policy: Optional[str] = None
    restart_count: int = 0

    # Health
    health_status: Optional[str] = None

    # Metadata
    compose_project: Optional[str] = None
    compose_service: Optional[str] = None


class ComposeStack(BaseModel):
    """Docker Compose stack information."""
    name: str
    path: str
    server: str

    # Compose file content
    compose_file: Optional[str] = None
    env_file: Optional[Dict[str, str]] = None

    # Services in this stack
    services: List[str] = Field(default_factory=list)
    containers: List[DockerContainer] = Field(default_factory=list)

    # Networks and volumes
    networks: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)

    # Metadata
    last_updated: Optional[datetime] = None
    version: Optional[str] = None


class DockerService(BaseModel):
    """High-level service information (can span multiple containers)."""
    name: str
    server: str
    criticality: Criticality = Criticality.NICE_TO_HAVE

    # Service type/category
    category: Optional[str] = None  # e.g., "media", "automation", "monitoring"
    type: Optional[str] = None  # e.g., "home-assistant", "immich", "traefik"

    # Containers
    containers: List[DockerContainer] = Field(default_factory=list)
    compose_stack: Optional[str] = None

    # Access information
    url: Optional[str] = None
    internal_url: Optional[str] = None
    ports: List[DockerPort] = Field(default_factory=list)

    # Dependencies
    depends_on: List[str] = Field(default_factory=list)
    required_by: List[str] = Field(default_factory=list)

    # Documentation
    description: Optional[str] = None
    purpose: Optional[str] = None
    ai_explanation: Optional[str] = None
    troubleshooting: Optional[str] = None

    # Authentication
    requires_auth: bool = False
    auth_method: Optional[str] = None
    credential_location: Optional[str] = None

    # Data
    data_locations: List[str] = Field(default_factory=list)
    backup_info: Optional[str] = None

    # Maintenance
    update_method: Optional[str] = None
    common_issues: List[str] = Field(default_factory=list)

    # External dependencies
    external_services: List[str] = Field(default_factory=list)
    api_keys_required: List[str] = Field(default_factory=list)

    # Metadata
    version: Optional[str] = None
    last_updated: Optional[datetime] = None
    uptime_percent: Optional[float] = None


class ReverseProxy(BaseModel):
    """Reverse proxy configuration."""
    name: str
    server: str
    type: str  # traefik, nginx, caddy
    config_path: str

    # Routes/services
    routes: List[Dict[str, Any]] = Field(default_factory=list)

    # SSL/TLS
    ssl_enabled: bool = False
    cert_provider: Optional[str] = None  # letsencrypt, self-signed, etc.

    # Metadata
    version: Optional[str] = None


class NetworkInfo(BaseModel):
    """Network topology and configuration."""
    # Tailscale
    tailscale_enabled: bool = False
    tailscale_devices: List[Dict[str, Any]] = Field(default_factory=list)

    # DNS
    dns_servers: List[str] = Field(default_factory=list)
    dns_records: List[Dict[str, str]] = Field(default_factory=list)

    # Firewall rules
    firewall_rules: List[Dict[str, Any]] = Field(default_factory=list)

    # Port forwarding
    port_forwards: List[Dict[str, Any]] = Field(default_factory=list)

    # Reverse proxies
    reverse_proxies: List[ReverseProxy] = Field(default_factory=list)


class InfrastructureSnapshot(BaseModel):
    """Complete snapshot of infrastructure at a point in time."""
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"

    # Infrastructure components
    servers: List[Server] = Field(default_factory=list)
    services: List[DockerService] = Field(default_factory=list)
    compose_stacks: List[ComposeStack] = Field(default_factory=list)
    network: Optional[NetworkInfo] = None

    # Statistics
    total_servers: int = 0
    total_services: int = 0
    total_containers: int = 0
    running_containers: int = 0

    # Scan metadata
    scan_duration_seconds: Optional[float] = None
    scan_errors: List[str] = Field(default_factory=list)
    scanners_used: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

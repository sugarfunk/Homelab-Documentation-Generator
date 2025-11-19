"""Data models for generated documentation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentationMode(str, Enum):
    """Documentation presentation mode."""
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"
    EMERGENCY = "emergency"


class DiagramFormat(str, Enum):
    """Diagram output format."""
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"


class OutputFormat(str, Enum):
    """Documentation output format."""
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"


class Diagram(BaseModel):
    """Generated diagram information."""
    title: str
    type: str  # topology, dependencies, network, data_flow
    format: DiagramFormat
    file_path: str
    description: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)


class Procedure(BaseModel):
    """Step-by-step procedure documentation."""
    title: str
    description: str
    steps: List[str]
    prerequisites: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    related_services: List[str] = Field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard
    estimated_time: Optional[str] = None


class TroubleshootingGuide(BaseModel):
    """Troubleshooting guide for a service or system."""
    title: str
    symptoms: List[str]
    possible_causes: List[str]
    solutions: List[str]
    prevention: Optional[str] = None
    related_docs: List[str] = Field(default_factory=list)


class ServerDocumentation(BaseModel):
    """Documentation for a single server."""
    server_name: str

    # Overview
    summary: str
    purpose: str
    criticality: str

    # Hardware & OS
    hardware_specs: Dict[str, str]
    os_info: Dict[str, str]

    # Network
    network_info: Dict[str, str]
    access_methods: List[Dict[str, str]]

    # Services
    hosted_services: List[str]
    service_count: int

    # Resources
    resource_usage: Dict[str, str]
    capacity_info: Optional[str] = None

    # Maintenance
    backup_schedule: Optional[str] = None
    backup_locations: List[str] = Field(default_factory=list)
    maintenance_tasks: List[str] = Field(default_factory=list)

    # Procedures
    access_procedure: Optional[Procedure] = None
    shutdown_procedure: Optional[Procedure] = None
    recovery_procedure: Optional[Procedure] = None

    # Non-technical explanation
    plain_english_summary: Optional[str] = None
    analogy: Optional[str] = None

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)


class ServiceDocumentation(BaseModel):
    """Documentation for a single service."""
    service_name: str

    # Overview
    summary: str
    purpose: str
    why_you_have_it: Optional[str] = None
    criticality: str
    category: Optional[str] = None

    # Access
    access_url: Optional[str] = None
    internal_url: Optional[str] = None
    ports: List[str] = Field(default_factory=list)
    requires_auth: bool = False
    credential_location: Optional[str] = None

    # Technical details
    server_location: str
    docker_info: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    reverse_dependencies: List[str] = Field(default_factory=list)

    # Data
    data_locations: List[str] = Field(default_factory=list)
    backup_info: Optional[str] = None
    data_size: Optional[str] = None

    # Configuration
    config_locations: List[str] = Field(default_factory=list)
    environment_vars: List[str] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)

    # Maintenance
    update_procedure: Optional[Procedure] = None
    backup_procedure: Optional[Procedure] = None
    restore_procedure: Optional[Procedure] = None

    # Troubleshooting
    common_issues: List[TroubleshootingGuide] = Field(default_factory=list)
    health_check: Optional[str] = None
    logs_location: Optional[str] = None

    # Non-technical explanation
    plain_english_summary: Optional[str] = None
    analogy: Optional[str] = None
    everyday_use_cases: List[str] = Field(default_factory=list)

    # Cost information
    subscription_cost: Optional[str] = None
    api_costs: Optional[str] = None

    # Metadata
    version: Optional[str] = None
    last_updated: Optional[datetime] = None
    generated_at: datetime = Field(default_factory=datetime.now)


class NetworkDocumentation(BaseModel):
    """Network topology and configuration documentation."""

    # Overview
    summary: str

    # Diagrams
    topology_diagram: Optional[Diagram] = None

    # Tailscale
    tailscale_info: Optional[Dict[str, Any]] = None
    tailscale_devices: List[Dict[str, str]] = Field(default_factory=list)

    # DNS
    dns_configuration: Dict[str, Any] = Field(default_factory=dict)
    dns_records: List[Dict[str, str]] = Field(default_factory=list)

    # Reverse Proxies
    reverse_proxy_info: List[Dict[str, Any]] = Field(default_factory=list)

    # SSL/TLS
    ssl_certificates: List[Dict[str, str]] = Field(default_factory=list)
    cert_renewal: Optional[str] = None

    # Firewall
    firewall_rules: List[Dict[str, str]] = Field(default_factory=list)
    port_forwards: List[Dict[str, str]] = Field(default_factory=list)

    # Procedures
    access_procedure: Optional[Procedure] = None

    # Non-technical explanation
    plain_english_summary: Optional[str] = None

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)


class EmergencyContact(BaseModel):
    """Emergency contact information."""
    name: str
    role: str
    phone: Optional[str] = None
    email: Optional[str] = None
    availability: Optional[str] = None
    expertise: List[str] = Field(default_factory=list)


class EmergencyGuide(BaseModel):
    """Emergency procedures and critical information."""

    # Password Manager
    password_manager_type: str
    password_manager_url: str
    password_manager_access: str
    emergency_access_procedure: Optional[Procedure] = None

    # Critical Services
    critical_services: List[Dict[str, str]]
    critical_urls: List[Dict[str, str]]

    # Contacts
    emergency_contacts: List[EmergencyContact]

    # Procedures
    emergency_shutdown: Procedure
    disaster_recovery: Procedure
    backup_restoration: Procedure

    # Backup Information
    backup_locations: List[Dict[str, str]]
    backup_schedule: str
    backup_verification: Optional[str] = None

    # Business Information (if applicable)
    business_info: Optional[Dict[str, Any]] = None
    client_contact_location: Optional[str] = None

    # Costs
    monthly_costs: List[Dict[str, str]] = Field(default_factory=list)
    annual_costs: List[Dict[str, str]] = Field(default_factory=list)
    total_monthly_cost: Optional[str] = None
    total_annual_cost: Optional[str] = None

    # "If I'm Dead" Instructions
    immediate_actions: List[str]
    within_24_hours: List[str]
    within_week: List[str]
    ongoing_maintenance: List[str]

    # What to Keep Running
    must_keep_running: List[str]
    can_shutdown_if_needed: List[str]

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)


class QuickReference(BaseModel):
    """Quick reference card for common tasks."""
    title: str
    category: str
    tasks: List[Dict[str, str]]  # {task: description/command}
    generated_at: datetime = Field(default_factory=datetime.now)


class GlossaryEntry(BaseModel):
    """Glossary entry for technical terms."""
    term: str
    definition: str
    plain_english: str
    analogy: Optional[str] = None
    related_terms: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)


class DocumentationBundle(BaseModel):
    """Complete documentation bundle."""
    title: str = "Homelab Documentation"
    subtitle: str = "Infrastructure Documentation and Emergency Guide"
    generated_at: datetime = Field(default_factory=datetime.now)
    version: str

    # Infrastructure Summary
    infrastructure_summary: Dict[str, Any]

    # Documentation Sections
    servers: List[ServerDocumentation]
    services: List[ServiceDocumentation]
    network: Optional[NetworkDocumentation] = None
    emergency: Optional[EmergencyGuide] = None

    # Diagrams
    diagrams: List[Diagram] = Field(default_factory=list)

    # Procedures
    procedures: List[Procedure] = Field(default_factory=list)

    # Quick References
    quick_references: List[QuickReference] = Field(default_factory=list)

    # Glossary
    glossary: List[GlossaryEntry] = Field(default_factory=list)

    # Change Log
    changes_since_last: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    mode: DocumentationMode = DocumentationMode.TECHNICAL
    formats: List[OutputFormat] = Field(default_factory=list)
    output_paths: Dict[str, str] = Field(default_factory=dict)

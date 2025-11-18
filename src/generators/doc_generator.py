"""Main documentation generator that orchestrates all documentation creation."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

from ..models.infrastructure import InfrastructureSnapshot, Server, DockerService
from ..models.documentation import (
    DocumentationBundle,
    ServerDocumentation,
    ServiceDocumentation,
    NetworkDocumentation,
    EmergencyGuide,
    EmergencyContact,
    Procedure,
    QuickReference,
    GlossaryEntry,
    DocumentationMode,
    OutputFormat,
)
from ..llm.multi_llm import MultiLLMClient
from ..llm import prompts
from ..utils.config import Config
from ..utils.security import sanitize_dict


class DocumentationGenerator:
    """Generates comprehensive documentation from infrastructure snapshots."""

    def __init__(self, config: Config):
        """Initialize documentation generator.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.llm_client = MultiLLMClient(config)
        self.output_dir = Path(config.documentation.output_dir)

    async def generate_full_documentation(
        self,
        snapshot: InfrastructureSnapshot,
        enable_ai: bool = True,
        modes: Optional[List[DocumentationMode]] = None
    ) -> DocumentationBundle:
        """Generate complete documentation bundle.

        Args:
            snapshot: Infrastructure snapshot
            enable_ai: Whether to use AI for enrichment
            modes: Documentation modes to generate

        Returns:
            Complete documentation bundle
        """
        self.logger.info("Starting documentation generation...")
        start_time = datetime.now()

        # Default to all modes if not specified
        if modes is None:
            modes = [DocumentationMode.TECHNICAL, DocumentationMode.NON_TECHNICAL, DocumentationMode.EMERGENCY]

        # Generate server documentation
        self.logger.info(f"Generating documentation for {len(snapshot.servers)} servers...")
        server_docs = await self._generate_server_docs(snapshot.servers, enable_ai)

        # Generate service documentation
        self.logger.info(f"Generating documentation for {len(snapshot.services)} services...")
        service_docs = await self._generate_service_docs(snapshot.services, enable_ai)

        # Generate network documentation
        self.logger.info("Generating network documentation...")
        network_doc = await self._generate_network_docs(snapshot, enable_ai)

        # Generate emergency guide
        self.logger.info("Generating emergency guide...")
        emergency_guide = await self._generate_emergency_guide(snapshot, enable_ai)

        # Generate procedures
        self.logger.info("Generating procedures...")
        procedures = await self._generate_procedures(snapshot, enable_ai)

        # Generate quick references
        self.logger.info("Generating quick reference cards...")
        quick_refs = self._generate_quick_references(snapshot)

        # Generate glossary
        self.logger.info("Generating glossary...")
        glossary = await self._generate_glossary(snapshot, enable_ai) if enable_ai else []

        # Create infrastructure summary
        infrastructure_summary = {
            "total_servers": snapshot.total_servers,
            "total_services": snapshot.total_services,
            "total_containers": snapshot.total_containers,
            "running_containers": snapshot.running_containers,
            "scan_timestamp": snapshot.timestamp.isoformat(),
            "scan_duration": f"{snapshot.scan_duration_seconds:.2f}s",
        }

        # Create documentation bundle
        bundle = DocumentationBundle(
            generated_at=datetime.now(),
            version=snapshot.version,
            infrastructure_summary=infrastructure_summary,
            servers=server_docs,
            services=service_docs,
            network=network_doc,
            emergency=emergency_guide,
            procedures=procedures,
            quick_references=quick_refs,
            glossary=glossary,
            mode=DocumentationMode.TECHNICAL,  # Primary mode
            formats=self.config.documentation.formats,
        )

        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Documentation generation complete in {duration:.2f}s")

        return bundle

    async def _generate_server_docs(
        self,
        servers: List[Server],
        enable_ai: bool
    ) -> List[ServerDocumentation]:
        """Generate documentation for all servers."""
        docs = []

        for server in servers:
            try:
                doc = await self._generate_server_doc(server, enable_ai)
                docs.append(doc)
            except Exception as e:
                self.logger.error(f"Failed to generate docs for {server.name}: {e}")

        return docs

    async def _generate_server_doc(
        self,
        server: Server,
        enable_ai: bool
    ) -> ServerDocumentation:
        """Generate documentation for a single server."""

        # Basic summary
        summary = f"{server.name} is a {server.role.value} server running {server.os_name or 'Unknown OS'}"

        # Hardware specs
        hardware_specs = {
            "CPU": server.cpu_model or "Unknown",
            "Cores": str(server.cpu_cores) if server.cpu_cores else "Unknown",
            "Memory": f"{server.total_memory_gb:.1f} GB" if server.total_memory_gb else "Unknown",
            "Architecture": server.architecture or "Unknown",
        }

        # OS info
        os_info = {
            "Operating System": server.os_name or "Unknown",
            "Version": server.os_version or "Unknown",
            "Kernel": server.kernel_version or "Unknown",
            "Docker": server.docker_version or "Not installed",
            "Docker Compose": server.docker_compose_version or "Not installed",
        }

        # Network info
        network_info = {
            "Hostname": server.hostname,
            "Tailscale IP": server.tailscale_ip or "N/A",
            "Local IP": server.local_ip or "N/A",
            "Public IP": server.public_ip or "N/A",
        }

        # Access methods
        access_methods = []
        if server.ssh:
            access_methods.append({
                "method": "SSH",
                "user": server.ssh.user,
                "port": str(server.ssh.port),
                "key": server.ssh.key_path or "Password-based",
            })

        # Resource usage
        resource_usage = {}
        if server.resources:
            resource_usage = {
                "CPU Usage": f"{server.resources.cpu_percent:.1f}%",
                "Memory Usage": f"{server.resources.memory_percent:.1f}% ({server.resources.memory_used_mb/1024:.1f}/{server.resources.memory_total_mb/1024:.1f} GB)",
                "Disk Usage": f"{server.resources.disk_percent:.1f}% ({server.resources.disk_used_gb:.1f}/{server.resources.disk_total_gb:.1f} GB)",
                "Uptime": f"{server.resources.uptime_seconds // 86400} days" if server.resources.uptime_seconds else "Unknown",
            }

        # Generate AI-powered plain English summary
        plain_english_summary = None
        analogy = None

        if enable_ai and self.config.llm.features.non_technical_mode:
            context = {
                "name": server.name,
                "role": server.role.value,
                "os": server.os_name or "Unknown",
                "purpose": server.purpose or "General purpose server",
            }

            prompt = prompts.generate_plain_english_summary(
                server.name,
                f"This is a {server.role.value} server running {server.os_name or 'Linux'}"
            )

            plain_english_summary = await self.llm_client.generate(
                prompt,
                is_sensitive=False,
                max_tokens=300
            )

        return ServerDocumentation(
            server_name=server.name,
            summary=summary,
            purpose=server.purpose or f"Acts as {server.role.value} in the infrastructure",
            criticality=server.criticality.value,
            hardware_specs=hardware_specs,
            os_info=os_info,
            network_info=network_info,
            access_methods=access_methods,
            hosted_services=[],  # Will be populated by linking services
            service_count=0,
            resource_usage=resource_usage,
            plain_english_summary=plain_english_summary,
            analogy=analogy,
        )

    async def _generate_service_docs(
        self,
        services: List[DockerService],
        enable_ai: bool
    ) -> List[ServiceDocumentation]:
        """Generate documentation for all services."""
        docs = []

        for service in services:
            try:
                doc = await self._generate_service_doc(service, enable_ai)
                docs.append(doc)
            except Exception as e:
                self.logger.error(f"Failed to generate docs for {service.name}: {e}")

        return docs

    async def _generate_service_doc(
        self,
        service: DockerService,
        enable_ai: bool
    ) -> ServiceDocumentation:
        """Generate documentation for a single service."""

        # Basic info
        summary = service.description or f"Docker service {service.name}"

        # Collect docker info
        docker_info = {
            "Containers": len(service.containers),
            "Status": "Running" if any(c.status.value == "running" for c in service.containers) else "Stopped",
            "Compose Stack": service.compose_stack or "Standalone",
        }

        if service.containers:
            container = service.containers[0]
            docker_info["Image"] = container.image
            if container.restart_policy:
                docker_info["Restart Policy"] = container.restart_policy

        # Ports
        ports = [f"{p.host_port}:{p.container_port}/{p.protocol}"
                for p in service.ports if p.host_port]

        # Generate AI explanations if enabled
        ai_explanation = None
        plain_english_summary = None

        if enable_ai and self.config.llm.features.service_explanations:
            # Get service explanation
            service_data = {
                "image": service.containers[0].image if service.containers else "unknown",
                "ports": ports,
                "type": service.type or "unknown",
            }

            prompt = prompts.generate_service_explanation(service.name, service_data)
            ai_explanation = await self.llm_client.generate(
                prompt,
                is_sensitive=False,
                max_tokens=500
            )

            # Get plain English summary for non-technical mode
            if self.config.llm.features.non_technical_mode and ai_explanation:
                plain_prompt = prompts.generate_plain_english_summary(
                    service.name,
                    ai_explanation
                )
                plain_english_summary = await self.llm_client.generate(
                    plain_prompt,
                    is_sensitive=False,
                    max_tokens=300
                )

        return ServiceDocumentation(
            service_name=service.name,
            summary=ai_explanation or summary,
            purpose=service.purpose or "Part of the homelab infrastructure",
            why_you_have_it=None,  # Could be AI-generated
            criticality=service.criticality.value,
            category=service.category,
            access_url=service.url,
            internal_url=service.internal_url,
            ports=ports,
            requires_auth=service.requires_auth,
            credential_location=service.credential_location or "See password manager",
            server_location=service.server,
            docker_info=docker_info,
            dependencies=service.depends_on,
            reverse_dependencies=service.required_by,
            data_locations=service.data_locations,
            backup_info=service.backup_info,
            config_locations=[],
            environment_vars=[],  # Sanitized in production
            external_dependencies=service.external_services,
            plain_english_summary=plain_english_summary,
            version=service.version,
            last_updated=service.last_updated,
        )

    async def _generate_network_docs(
        self,
        snapshot: InfrastructureSnapshot,
        enable_ai: bool
    ) -> Optional[NetworkDocumentation]:
        """Generate network documentation."""

        # Collect reverse proxy info
        reverse_proxy_info = []
        for proxy_config in self.config.infrastructure.reverse_proxies:
            reverse_proxy_info.append({
                "name": proxy_config.name,
                "server": proxy_config.server,
                "type": proxy_config.type,
                "config_path": proxy_config.config_path,
            })

        # Generate plain English summary
        plain_english_summary = None
        if enable_ai and self.config.llm.features.non_technical_mode:
            prompt = """Explain in simple terms what a home network looks like with:
            - Multiple servers connected via Tailscale VPN
            - Reverse proxies routing traffic to services
            - Docker containers running services

            Keep it under 150 words and avoid jargon."""

            plain_english_summary = await self.llm_client.generate(
                prompt,
                is_sensitive=False,
                max_tokens=300
            )

        return NetworkDocumentation(
            summary="Infrastructure network configuration",
            reverse_proxy_info=reverse_proxy_info,
            plain_english_summary=plain_english_summary,
        )

    async def _generate_emergency_guide(
        self,
        snapshot: InfrastructureSnapshot,
        enable_ai: bool
    ) -> EmergencyGuide:
        """Generate emergency procedures and critical information."""

        # Get emergency config
        emergency_config = self.config.emergency

        # Convert contacts
        contacts = [
            EmergencyContact(
                name=c.name,
                role=c.role,
                phone=c.phone,
                email=c.email,
            )
            for c in emergency_config.contacts
        ]

        # Critical services
        critical_services = []
        for service in snapshot.services:
            if service.criticality.value == "critical":
                critical_services.append({
                    "name": service.name,
                    "url": service.url or "N/A",
                    "server": service.server,
                    "why_critical": "Essential for operations",
                })

        # Create emergency procedures
        emergency_shutdown = Procedure(
            title="Emergency Shutdown",
            description="How to safely shut down all infrastructure",
            steps=[
                "Stop all non-critical services first",
                "Stop critical services",
                "Shut down servers in reverse order of importance",
                "Document what was shut down and why",
            ],
            prerequisites=["SSH access to all servers", "List of service dependencies"],
            warnings=["Ensure backups are up to date before shutdown"],
        )

        disaster_recovery = Procedure(
            title="Disaster Recovery",
            description="How to recover from catastrophic failure",
            steps=[
                "Assess what is down and what is still working",
                "Check backup integrity",
                "Restore critical services first",
                "Verify data integrity",
                "Restore non-critical services",
                "Update documentation with what happened",
            ],
            prerequisites=["Access to backups", "Fresh server or VM"],
            warnings=["Do not overwrite good backups with corrupted data"],
        )

        backup_restoration = Procedure(
            title="Restore from Backup",
            description="How to restore services from backup",
            steps=[
                "Identify which backup to use",
                "Verify backup integrity",
                "Stop the service if running",
                "Restore data to correct location",
                "Start the service",
                "Verify service is working correctly",
            ],
            prerequisites=["Backup location access", "Sufficient disk space"],
        )

        # Password manager info
        pm_info = emergency_config.password_manager

        # Immediate actions list
        immediate_actions = [
            f"Access password manager: {pm_info.get('url', 'See documentation')}",
            "Check which services are running",
            "Review this emergency guide fully",
            "Contact emergency contacts if needed",
        ]

        within_24_hours = [
            "Verify all backups are current",
            "Check for any error notifications",
            "Review recent changes if something broke",
            "Document the situation",
        ]

        within_week = [
            "Ensure all services are stable",
            "Update documentation if anything changed",
            "Consider what could be improved",
        ]

        ongoing_maintenance = [
            "Weekly: Check all services are running",
            "Monthly: Verify backups",
            "Quarterly: Review and update documentation",
            "Annually: Review costs and optimize",
        ]

        return EmergencyGuide(
            password_manager_type=pm_info.get('type', 'Unknown'),
            password_manager_url=pm_info.get('url', ''),
            password_manager_access=pm_info.get('emergency_access', 'See documentation'),
            critical_services=critical_services,
            critical_urls=[{"name": s["name"], "url": s["url"]} for s in critical_services],
            emergency_contacts=contacts,
            emergency_shutdown=emergency_shutdown,
            disaster_recovery=disaster_recovery,
            backup_restoration=backup_restoration,
            backup_locations=[
                {"name": b.get('location', ''), "path": b.get('path', ''), "type": b.get('type', '')}
                for b in emergency_config.backups
            ],
            backup_schedule="See individual service documentation",
            immediate_actions=immediate_actions,
            within_24_hours=within_24_hours,
            within_week=within_week,
            ongoing_maintenance=ongoing_maintenance,
            must_keep_running=[s.name for s in snapshot.services if s.criticality.value == "critical"],
            can_shutdown_if_needed=[s.name for s in snapshot.services if s.criticality.value == "nice-to-have"],
        )

    async def _generate_procedures(
        self,
        snapshot: InfrastructureSnapshot,
        enable_ai: bool
    ) -> List[Procedure]:
        """Generate common procedures."""
        procedures = []

        # Access procedure
        procedures.append(Procedure(
            title="Access a Server",
            description="How to connect to any server",
            steps=[
                "Ensure you're connected to Tailscale VPN (if using)",
                "Open terminal",
                "Use SSH: ssh user@server-ip",
                "Enter password or use SSH key",
            ],
            prerequisites=["Tailscale installed", "SSH client", "Credentials"],
        ))

        # Restart service procedure
        procedures.append(Procedure(
            title="Restart a Docker Service",
            description="How to restart any Docker service",
            steps=[
                "SSH into the server hosting the service",
                "Find the container: docker ps | grep service-name",
                "Restart: docker restart container-name",
                "Check logs: docker logs container-name",
                "Verify it's running: docker ps",
            ],
            prerequisites=["SSH access", "Docker commands knowledge"],
        ))

        return procedures

    def _generate_quick_references(
        self,
        snapshot: InfrastructureSnapshot
    ) -> List[QuickReference]:
        """Generate quick reference cards."""
        refs = []

        # Docker commands
        refs.append(QuickReference(
            title="Common Docker Commands",
            category="Docker",
            tasks=[
                {"List containers": "docker ps"},
                {"View logs": "docker logs <container>"},
                {"Restart container": "docker restart <container>"},
                {"Stop container": "docker stop <container>"},
                {"Enter container": "docker exec -it <container> /bin/bash"},
                {"View compose services": "docker-compose ps"},
                {"Restart compose stack": "docker-compose restart"},
            ]
        ))

        # Server commands
        refs.append(QuickReference(
            title="Server Management",
            category="System",
            tasks=[
                {"Check disk space": "df -h"},
                {"Check memory": "free -h"},
                {"Check CPU": "top"},
                {"View running processes": "ps aux"},
                {"Restart server": "sudo reboot"},
                {"Check logs": "journalctl -xe"},
            ]
        ))

        return refs

    async def _generate_glossary(
        self,
        snapshot: InfrastructureSnapshot,
        enable_ai: bool
    ) -> List[GlossaryEntry]:
        """Generate glossary of technical terms."""
        glossary = []

        # Common terms
        terms = [
            ("Docker", "containerization"),
            ("Container", "isolated application"),
            ("Compose", "multi-container orchestration"),
            ("Reverse Proxy", "traffic routing"),
            ("VPN", "secure network connection"),
            ("SSH", "remote access"),
        ]

        for term, context in terms[:3]:  # Limit to avoid too many API calls
            if enable_ai:
                prompt = prompts.generate_glossary_entry(term, context)
                response = await self.llm_client.generate(
                    prompt,
                    is_sensitive=False,
                    max_tokens=300
                )

                if response:
                    # Parse response (simplified)
                    glossary.append(GlossaryEntry(
                        term=term,
                        definition=f"Definition of {term}",
                        plain_english=response[:200] if response else f"A {context} tool",
                    ))

        return glossary

    async def save_bundle(
        self,
        bundle: DocumentationBundle,
        output_dir: Optional[Path] = None
    ) -> Path:
        """Save documentation bundle to disk.

        Args:
            bundle: Documentation bundle to save
            output_dir: Output directory (uses config default if None)

        Returns:
            Path to saved bundle
        """
        if output_dir is None:
            output_dir = self.output_dir

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        bundle_path = output_dir / f"documentation-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        with open(bundle_path, 'w') as f:
            json.dump(bundle.dict(), f, indent=2, default=str)

        self.logger.info(f"Documentation bundle saved to: {bundle_path}")

        # Also save as latest
        latest_path = output_dir / "documentation-latest.json"
        with open(latest_path, 'w') as f:
            json.dump(bundle.dict(), f, indent=2, default=str)

        return bundle_path

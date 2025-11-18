"""Main scanner orchestrator that coordinates all infrastructure scanning."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from .models.infrastructure import InfrastructureSnapshot, Server, DockerService, ComposeStack
from .scanners import ServerScanner, DockerScanner, ComposeScanner
from .utils.config import Config


class ScannerOrchestrator:
    """Coordinates all infrastructure scanning operations."""

    def __init__(self, config: Config):
        """Initialize orchestrator.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize scanners
        self.server_scanner = ServerScanner(config)
        self.docker_scanner = DockerScanner(config)
        self.compose_scanner = ComposeScanner(config)

    async def scan_all(self) -> InfrastructureSnapshot:
        """Perform a complete infrastructure scan.

        Returns:
            InfrastructureSnapshot with all collected data
        """
        start_time = datetime.now()
        self.logger.info("Starting full infrastructure scan...")

        all_servers = []
        all_services = []
        all_compose_stacks = []
        scan_errors = []
        scanners_used = []

        # Scan each configured server
        for server_config in self.config.infrastructure.servers:
            try:
                self.logger.info(f"Scanning server: {server_config.name}")

                # Scan server information
                if "server_info" in self.config.scanning.enabled_scanners:
                    server = await self.server_scanner.scan(server_config)
                    if server:
                        all_servers.append(server)
                        scan_errors.extend(self.server_scanner.get_errors())

                        if "server_info" not in scanners_used:
                            scanners_used.append("server_info")

                # Scan Docker containers
                if "docker" in self.config.scanning.enabled_scanners:
                    docker_result = await self.docker_scanner.scan(server_config)
                    if docker_result:
                        all_services.extend(docker_result['services'])
                        scan_errors.extend(self.docker_scanner.get_errors())

                        if "docker" not in scanners_used:
                            scanners_used.append("docker")

                # Scan Docker Compose files
                if "compose_files" in self.config.scanning.enabled_scanners:
                    compose_stacks = await self.compose_scanner.scan(server_config)
                    if compose_stacks:
                        all_compose_stacks.extend(compose_stacks)
                        scan_errors.extend(self.compose_scanner.get_errors())

                        if "compose_files" not in scanners_used:
                            scanners_used.append("compose_files")

            except Exception as e:
                error_msg = f"Failed to scan server {server_config.name}: {str(e)}"
                self.logger.error(error_msg)
                scan_errors.append(error_msg)

        # Calculate statistics
        total_servers = len(all_servers)
        total_services = len(all_services)
        total_containers = sum(len(service.containers) for service in all_services)
        running_containers = sum(
            sum(1 for container in service.containers if container.status.value == "running")
            for service in all_services
        )

        scan_duration = (datetime.now() - start_time).total_seconds()

        # Create snapshot
        snapshot = InfrastructureSnapshot(
            timestamp=datetime.now(),
            servers=all_servers,
            services=all_services,
            compose_stacks=all_compose_stacks,
            total_servers=total_servers,
            total_services=total_services,
            total_containers=total_containers,
            running_containers=running_containers,
            scan_duration_seconds=scan_duration,
            scan_errors=scan_errors,
            scanners_used=scanners_used,
        )

        self.logger.info(
            f"Scan complete: {total_servers} servers, {total_services} services, "
            f"{total_containers} containers ({running_containers} running) "
            f"in {scan_duration:.2f}s"
        )

        if scan_errors:
            self.logger.warning(f"Scan completed with {len(scan_errors)} errors")

        return snapshot

    async def scan_server(self, server_name: str) -> Optional[Server]:
        """Scan a single server.

        Args:
            server_name: Name of server to scan

        Returns:
            Server information or None
        """
        for server_config in self.config.infrastructure.servers:
            if server_config.name == server_name:
                return await self.server_scanner.scan(server_config)

        self.logger.error(f"Server not found in configuration: {server_name}")
        return None

    async def scan_docker_on_server(self, server_name: str) -> List[DockerService]:
        """Scan Docker services on a specific server.

        Args:
            server_name: Name of server to scan

        Returns:
            List of Docker services
        """
        for server_config in self.config.infrastructure.servers:
            if server_config.name == server_name:
                result = await self.docker_scanner.scan(server_config)
                return result.get('services', [])

        self.logger.error(f"Server not found in configuration: {server_name}")
        return []

    async def scan_compose_on_server(self, server_name: str) -> List[ComposeStack]:
        """Scan Docker Compose stacks on a specific server.

        Args:
            server_name: Name of server to scan

        Returns:
            List of compose stacks
        """
        for server_config in self.config.infrastructure.servers:
            if server_config.name == server_name:
                return await self.compose_scanner.scan(server_config)

        self.logger.error(f"Server not found in configuration: {server_name}")
        return []

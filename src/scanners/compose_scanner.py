"""Docker Compose file scanner."""

import asyncio
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import paramiko
from .base import BaseScanner
from ..models.infrastructure import ComposeStack
from datetime import datetime


class ComposeScanner(BaseScanner):
    """Scanner for Docker Compose files."""

    def __init__(self, config: Any):
        """Initialize compose scanner.

        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.compose_paths = config.infrastructure.docker_compose_paths or []

    async def scan(self, server_config: Any) -> List[ComposeStack]:
        """Scan for docker-compose files on a server.

        Args:
            server_config: Server configuration

        Returns:
            List of compose stacks found
        """
        self.clear_errors()
        stacks = []

        for compose_path in self.compose_paths:
            try:
                if server_config.ssh:
                    stack = await self._scan_remote_compose(server_config, compose_path)
                else:
                    stack = await self._scan_local_compose(server_config, compose_path)

                if stack:
                    stacks.extend(stack)

            except Exception as e:
                self.add_error(f"Failed to scan compose path {compose_path}: {str(e)}")

        return stacks

    async def _scan_local_compose(
        self,
        server_config: Any,
        base_path: str
    ) -> List[ComposeStack]:
        """Scan local filesystem for compose files.

        Args:
            server_config: Server configuration
            base_path: Base path to search

        Returns:
            List of compose stacks
        """
        stacks = []
        base = Path(base_path).expanduser()

        if not base.exists():
            self.logger.warning(f"Compose path does not exist: {base_path}")
            return []

        # Find all docker-compose.yml files
        compose_files = []
        if base.is_dir():
            compose_files.extend(base.glob('**/docker-compose.yml'))
            compose_files.extend(base.glob('**/docker-compose.yaml'))
        elif base.is_file() and 'docker-compose' in base.name:
            compose_files.append(base)

        for compose_file in compose_files:
            try:
                stack = self._parse_compose_file(
                    server_config.name,
                    str(compose_file),
                    compose_file.read_text()
                )
                if stack:
                    stacks.append(stack)
            except Exception as e:
                self.add_error(f"Failed to parse {compose_file}: {str(e)}")

        return stacks

    async def _scan_remote_compose(
        self,
        server_config: Any,
        base_path: str
    ) -> List[ComposeStack]:
        """Scan remote server for compose files via SSH.

        Args:
            server_config: Server configuration
            base_path: Base path to search

        Returns:
            List of compose stacks
        """
        stacks = []
        ssh = None

        try:
            # Connect via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            hostname = server_config.tailscale_ip or server_config.local_ip or server_config.hostname
            username = server_config.ssh.user
            port = server_config.ssh.port or 22

            if server_config.ssh.key_path:
                ssh.connect(
                    hostname=hostname,
                    username=username,
                    key_filename=server_config.ssh.key_path,
                    port=port,
                    timeout=self.config.scanning.timeouts.get("ssh_connection", 30)
                )
            elif server_config.ssh.password:
                ssh.connect(
                    hostname=hostname,
                    username=username,
                    password=server_config.ssh.password,
                    port=port,
                    timeout=self.config.scanning.timeouts.get("ssh_connection", 30)
                )

            # Find docker-compose files
            find_cmd = f'find {base_path} -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null'
            stdin, stdout, stderr = ssh.exec_command(find_cmd)
            compose_files = stdout.read().decode('utf-8').strip().split('\n')

            for compose_file_path in compose_files:
                if not compose_file_path:
                    continue

                try:
                    # Read the compose file
                    stdin, stdout, stderr = ssh.exec_command(f'cat {compose_file_path}')
                    compose_content = stdout.read().decode('utf-8')

                    stack = self._parse_compose_file(
                        server_config.name,
                        compose_file_path,
                        compose_content
                    )
                    if stack:
                        stacks.append(stack)

                except Exception as e:
                    self.add_error(f"Failed to read {compose_file_path}: {str(e)}")

        except Exception as e:
            self.add_error(f"Remote compose scan failed: {str(e)}")

        finally:
            if ssh:
                ssh.close()

        return stacks

    def _parse_compose_file(
        self,
        server_name: str,
        file_path: str,
        content: str
    ) -> Optional[ComposeStack]:
        """Parse a docker-compose file.

        Args:
            server_name: Name of server
            file_path: Path to compose file
            content: File content

        Returns:
            ComposeStack or None
        """
        try:
            compose_data = yaml.safe_load(content)

            if not compose_data:
                return None

            # Extract project name from path or compose file
            project_name = Path(file_path).parent.name

            # Override with compose project name if specified
            if isinstance(compose_data, dict):
                project_name = compose_data.get('name', project_name)

            # Get services
            services = []
            if 'services' in compose_data:
                services = list(compose_data['services'].keys())

            # Get networks
            networks = []
            if 'networks' in compose_data:
                networks = list(compose_data['networks'].keys())

            # Get volumes
            volumes = []
            if 'volumes' in compose_data:
                volumes = list(compose_data['volumes'].keys())

            # Get version
            version = compose_data.get('version', 'unknown')

            stack = ComposeStack(
                name=project_name,
                path=file_path,
                server=server_name,
                compose_file=content,
                services=services,
                networks=networks,
                volumes=volumes,
                version=version,
                last_updated=datetime.now(),
            )

            return stack

        except yaml.YAMLError as e:
            self.add_error(f"YAML parse error in {file_path}: {str(e)}")
            return None
        except Exception as e:
            self.add_error(f"Failed to parse compose file {file_path}: {str(e)}")
            return None

    def extract_service_info(self, stack: ComposeStack, service_name: str) -> Optional[Dict[str, Any]]:
        """Extract detailed information about a service from compose file.

        Args:
            stack: Compose stack
            service_name: Name of service

        Returns:
            Service configuration dictionary
        """
        try:
            compose_data = yaml.safe_load(stack.compose_file)

            if 'services' in compose_data and service_name in compose_data['services']:
                return compose_data['services'][service_name]

        except Exception as e:
            self.logger.warning(f"Failed to extract service info: {str(e)}")

        return None

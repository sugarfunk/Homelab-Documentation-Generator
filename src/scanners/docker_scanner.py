"""Docker infrastructure scanner."""

import asyncio
import docker
from datetime import datetime
from typing import Dict, List, Optional, Any
import paramiko
from .base import BaseScanner
from ..models.infrastructure import (
    DockerContainer,
    DockerPort,
    DockerService,
    ServiceStatus,
    Criticality,
)


class DockerScanner(BaseScanner):
    """Scanner for Docker containers and services."""

    def __init__(self, config: Any):
        """Initialize Docker scanner.

        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.timeout = config.scanning.timeouts.get("docker_api", 60)

    async def scan(self, server_config: Any) -> Dict[str, Any]:
        """Scan Docker containers on a server.

        Args:
            server_config: Server configuration

        Returns:
            Dictionary with containers and services
        """
        self.clear_errors()

        try:
            # Connect to Docker (either local or remote via SSH)
            if server_config.ssh:
                containers = await self._scan_remote_docker(server_config)
            else:
                containers = await self._scan_local_docker()

            # Group containers into services
            services = self._group_containers_into_services(containers, server_config.name)

            return {
                "containers": containers,
                "services": services,
                "container_count": len(containers),
                "service_count": len(services),
                "running_count": sum(1 for c in containers if c.status == ServiceStatus.RUNNING),
            }

        except Exception as e:
            self.add_error(f"Failed to scan Docker on {server_config.name}: {str(e)}")
            return {
                "containers": [],
                "services": [],
                "container_count": 0,
                "service_count": 0,
                "running_count": 0,
            }

    async def _scan_local_docker(self) -> List[DockerContainer]:
        """Scan local Docker instance.

        Returns:
            List of containers
        """
        try:
            client = docker.from_env()
            containers = client.containers.list(all=True)
            return [self._parse_container(c) for c in containers]
        except Exception as e:
            self.add_error(f"Local Docker scan failed: {str(e)}")
            return []

    async def _scan_remote_docker(self, server_config: Any) -> List[DockerContainer]:
        """Scan remote Docker instance via SSH.

        Args:
            server_config: Server configuration

        Returns:
            List of containers
        """
        try:
            # Execute docker commands via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Determine connection parameters
            hostname = server_config.tailscale_ip or server_config.local_ip or server_config.hostname
            username = server_config.ssh.user
            port = server_config.ssh.port or 22

            # Connect
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
            else:
                raise ValueError("No SSH authentication method provided")

            # Get container list
            stdin, stdout, stderr = ssh.exec_command("docker ps -a --format '{{json .}}'")
            container_lines = stdout.read().decode('utf-8').strip().split('\n')

            containers = []
            for line in container_lines:
                if line:
                    try:
                        import json
                        container_json = json.loads(line)
                        container = await self._parse_remote_container(ssh, container_json)
                        if container:
                            containers.append(container)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse container JSON: {line}")

            ssh.close()
            return containers

        except Exception as e:
            self.add_error(f"Remote Docker scan failed: {str(e)}")
            return []

    def _parse_container(self, container: Any) -> DockerContainer:
        """Parse Docker container object into our model.

        Args:
            container: Docker container object

        Returns:
            DockerContainer model
        """
        attrs = container.attrs

        # Parse ports
        ports = []
        if 'NetworkSettings' in attrs and 'Ports' in attrs['NetworkSettings']:
            for container_port, host_bindings in attrs['NetworkSettings']['Ports'].items():
                if host_bindings:
                    for binding in host_bindings:
                        port_num, protocol = container_port.split('/')
                        ports.append(DockerPort(
                            container_port=int(port_num),
                            host_port=int(binding.get('HostPort', 0)),
                            protocol=protocol,
                            host_ip=binding.get('HostIp', '0.0.0.0')
                        ))

        # Parse environment variables
        env_dict = {}
        if 'Config' in attrs and 'Env' in attrs['Config']:
            for env_var in attrs['Config']['Env']:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env_dict[key] = value

        # Parse labels
        labels = attrs.get('Config', {}).get('Labels', {}) or {}

        # Determine compose project and service
        compose_project = labels.get('com.docker.compose.project')
        compose_service = labels.get('com.docker.compose.service')

        # Parse created time
        created_str = attrs.get('Created', '')
        created = None
        if created_str:
            try:
                created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except:
                pass

        # Parse started time
        started = None
        if 'State' in attrs and 'StartedAt' in attrs['State']:
            started_str = attrs['State']['StartedAt']
            if started_str and started_str != '0001-01-01T00:00:00Z':
                try:
                    started = datetime.fromisoformat(started_str.replace('Z', '+00:00'))
                except:
                    pass

        # Map status
        state = attrs.get('State', {}).get('Status', 'unknown')
        status_map = {
            'running': ServiceStatus.RUNNING,
            'exited': ServiceStatus.STOPPED,
            'paused': ServiceStatus.PAUSED,
            'restarting': ServiceStatus.RESTARTING,
            'dead': ServiceStatus.DEAD,
        }
        status = status_map.get(state, ServiceStatus.UNKNOWN)

        return DockerContainer(
            id=container.id,
            name=container.name.lstrip('/'),
            image=attrs.get('Config', {}).get('Image', 'unknown'),
            status=status,
            state=state,
            command=attrs.get('Config', {}).get('Cmd'),
            entrypoint=attrs.get('Config', {}).get('Entrypoint'),
            environment=env_dict,
            labels=labels,
            ports=ports,
            networks=list(attrs.get('NetworkSettings', {}).get('Networks', {}).keys()),
            volumes=[],  # TODO: Parse volumes
            mounts=attrs.get('Mounts', []),
            created=created,
            started=started,
            restart_policy=attrs.get('HostConfig', {}).get('RestartPolicy', {}).get('Name'),
            restart_count=attrs.get('RestartCount', 0),
            health_status=attrs.get('State', {}).get('Health', {}).get('Status'),
            compose_project=compose_project,
            compose_service=compose_service,
        )

    async def _parse_remote_container(self, ssh: paramiko.SSHClient, container_json: Dict[str, Any]) -> Optional[DockerContainer]:
        """Parse remote container from JSON output.

        Args:
            ssh: SSH client
            container_json: Container JSON from docker ps

        Returns:
            DockerContainer or None
        """
        try:
            container_id = container_json.get('ID', '')

            # Get detailed info
            stdin, stdout, stderr = ssh.exec_command(f"docker inspect {container_id}")
            inspect_output = stdout.read().decode('utf-8')

            import json
            inspect_data = json.loads(inspect_output)[0]

            # Parse similar to _parse_container
            # (Simplified version - reuse logic from above)

            return DockerContainer(
                id=container_id,
                name=container_json.get('Names', '').lstrip('/'),
                image=container_json.get('Image', ''),
                status=ServiceStatus.RUNNING if container_json.get('State') == 'running' else ServiceStatus.STOPPED,
                state=container_json.get('State', 'unknown'),
                command=container_json.get('Command', ''),
                environment={},  # TODO: Parse from inspect
                labels={},
                ports=[],  # TODO: Parse ports
                networks=[],
                volumes=[],
                mounts=[],
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse remote container: {str(e)}")
            return None

    def _group_containers_into_services(
        self,
        containers: List[DockerContainer],
        server_name: str
    ) -> List[DockerService]:
        """Group containers into logical services.

        Args:
            containers: List of containers
            server_name: Name of server

        Returns:
            List of services
        """
        services_dict: Dict[str, List[DockerContainer]] = {}

        for container in containers:
            # Use compose service name if available, otherwise container name
            service_name = container.compose_service or container.name

            if service_name not in services_dict:
                services_dict[service_name] = []
            services_dict[service_name].append(container)

        # Create DockerService objects
        services = []
        for service_name, service_containers in services_dict.items():
            # Determine criticality from labels or defaults
            criticality = Criticality.NICE_TO_HAVE
            for container in service_containers:
                crit_label = container.labels.get('homelab.criticality')
                if crit_label:
                    try:
                        criticality = Criticality(crit_label)
                        break
                    except ValueError:
                        pass

            # Get URLs from labels
            url = None
            for container in service_containers:
                traefik_host = container.labels.get('traefik.http.routers.' + service_name + '.rule')
                if traefik_host and 'Host(' in traefik_host:
                    import re
                    match = re.search(r'Host\(`([^`]+)`\)', traefik_host)
                    if match:
                        url = f"https://{match.group(1)}"
                        break

            # Collect all ports
            all_ports = []
            for container in service_containers:
                all_ports.extend(container.ports)

            service = DockerService(
                name=service_name,
                server=server_name,
                criticality=criticality,
                containers=service_containers,
                compose_stack=service_containers[0].compose_project if service_containers else None,
                url=url,
                ports=all_ports,
            )
            services.append(service)

        return services

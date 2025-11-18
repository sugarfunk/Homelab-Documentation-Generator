"""Server information scanner."""

import asyncio
import platform
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import paramiko
import json
from .base import BaseScanner
from ..models.infrastructure import (
    Server,
    ServerRole,
    Criticality,
    ResourceUsage,
    NetworkInterface,
    SSHConfig,
)


class ServerScanner(BaseScanner):
    """Scanner for server hardware and OS information."""

    def __init__(self, config: Any):
        """Initialize server scanner.

        Args:
            config: Configuration object
        """
        super().__init__(config)

    async def scan(self, server_config: Any) -> Optional[Server]:
        """Scan a server for hardware, OS, and resource information.

        Args:
            server_config: Server configuration

        Returns:
            Server model with collected information
        """
        self.clear_errors()

        try:
            # Determine if this is local or remote scan
            is_local = self._is_local_server(server_config)

            if is_local:
                server_info = await self._scan_local_server(server_config)
            else:
                server_info = await self._scan_remote_server(server_config)

            return server_info

        except Exception as e:
            self.add_error(f"Failed to scan server {server_config.name}: {str(e)}")
            # Return minimal server info
            return Server(
                name=server_config.name,
                hostname=server_config.hostname,
                role=ServerRole(server_config.role),
                criticality=Criticality(server_config.criticality),
                tailscale_ip=server_config.tailscale_ip,
                local_ip=server_config.local_ip,
                public_ip=getattr(server_config, 'public_ip', None),
                ssh=SSHConfig(**server_config.ssh.dict()) if server_config.ssh else None,
                reachable=False,
                scan_errors=self.errors,
                last_scanned=datetime.now(),
            )

    def _is_local_server(self, server_config: Any) -> bool:
        """Check if server is the local machine.

        Args:
            server_config: Server configuration

        Returns:
            bool: True if local server
        """
        local_hostname = platform.node()
        return (
            server_config.hostname == local_hostname or
            server_config.hostname == 'localhost' or
            server_config.hostname == '127.0.0.1'
        )

    async def _scan_local_server(self, server_config: Any) -> Server:
        """Scan local server information.

        Args:
            server_config: Server configuration

        Returns:
            Server model
        """
        # Get OS information
        os_info = platform.uname()

        # Get CPU information
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)

        # Get memory information
        memory = psutil.virtual_memory()

        # Get disk information
        disk = psutil.disk_usage('/')

        # Get resource usage
        resources = ResourceUsage(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_used_mb=memory.used / 1024 / 1024,
            memory_total_mb=memory.total / 1024 / 1024,
            memory_percent=memory.percent,
            disk_used_gb=disk.used / 1024 / 1024 / 1024,
            disk_total_gb=disk.total / 1024 / 1024 / 1024,
            disk_percent=disk.percent,
            load_average=list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
            uptime_seconds=int(datetime.now().timestamp() - psutil.boot_time()),
        )

        # Get network interfaces
        interfaces = []
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()

        for interface_name, addrs in net_if_addrs.items():
            if interface_name in net_if_stats:
                stats = net_if_stats[interface_name]
                ip_address = None
                mac_address = None

                for addr in addrs:
                    if addr.family == 2:  # AF_INET (IPv4)
                        ip_address = addr.address
                    elif addr.family == 17:  # AF_PACKET (MAC)
                        mac_address = addr.address

                interfaces.append(NetworkInterface(
                    name=interface_name,
                    ip_address=ip_address,
                    mac_address=mac_address,
                    is_up=stats.isup,
                    speed_mbps=stats.speed if stats.speed > 0 else None,
                ))

        # Check Docker version
        docker_version = None
        docker_compose_version = None
        try:
            import docker
            client = docker.from_env()
            docker_version = client.version().get('Version')
        except:
            pass

        try:
            import subprocess
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                docker_compose_version = result.stdout.strip()
        except:
            pass

        return Server(
            name=server_config.name,
            hostname=server_config.hostname,
            role=ServerRole(server_config.role),
            criticality=Criticality(server_config.criticality),
            tailscale_ip=server_config.tailscale_ip,
            local_ip=server_config.local_ip,
            public_ip=getattr(server_config, 'public_ip', None),
            interfaces=interfaces,
            ssh=SSHConfig(**server_config.ssh.dict()) if server_config.ssh else None,
            os_name=os_info.system,
            os_version=os_info.release,
            kernel_version=os_info.version,
            architecture=os_info.machine,
            cpu_model=platform.processor() or f"{cpu_count} cores",
            cpu_cores=cpu_count_logical,
            total_memory_gb=memory.total / 1024 / 1024 / 1024,
            resources=resources,
            docker_version=docker_version,
            docker_compose_version=docker_compose_version,
            last_scanned=datetime.now(),
            reachable=True,
            notes=getattr(server_config, 'notes', None),
            purpose=getattr(server_config, 'purpose', None),
        )

    async def _scan_remote_server(self, server_config: Any) -> Server:
        """Scan remote server via SSH.

        Args:
            server_config: Server configuration

        Returns:
            Server model
        """
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
            else:
                raise ValueError("No SSH authentication method provided")

            # Gather information via commands
            commands = {
                'os_name': 'cat /etc/os-release | grep "^NAME=" | cut -d= -f2 | tr -d \\"',
                'os_version': 'cat /etc/os-release | grep "^VERSION=" | cut -d= -f2 | tr -d \\"',
                'kernel': 'uname -r',
                'architecture': 'uname -m',
                'cpu_model': 'lscpu | grep "Model name:" | cut -d: -f2 | xargs',
                'cpu_cores': 'nproc',
                'memory_total': 'free -m | grep Mem: | awk \'{print $2}\'',
                'memory_used': 'free -m | grep Mem: | awk \'{print $3}\'',
                'disk_total': 'df -BG / | tail -1 | awk \'{print $2}\' | tr -d G',
                'disk_used': 'df -BG / | tail -1 | awk \'{print $3}\' | tr -d G',
                'uptime': 'cat /proc/uptime | cut -d. -f1',
                'load_avg': 'cat /proc/loadavg | awk \'{print $1,$2,$3}\'',
                'docker_version': 'docker --version 2>/dev/null || echo ""',
                'docker_compose_version': 'docker-compose --version 2>/dev/null || echo ""',
            }

            results = {}
            for key, command in commands.items():
                try:
                    stdin, stdout, stderr = ssh.exec_command(command)
                    results[key] = stdout.read().decode('utf-8').strip()
                except Exception as e:
                    self.logger.warning(f"Command '{command}' failed: {str(e)}")
                    results[key] = ""

            # Parse results
            cpu_cores = int(results.get('cpu_cores', 0)) if results.get('cpu_cores', '').isdigit() else 0
            memory_total_mb = float(results.get('memory_total', 0)) if results.get('memory_total', '').replace('.', '').isdigit() else 0
            memory_used_mb = float(results.get('memory_used', 0)) if results.get('memory_used', '').replace('.', '').isdigit() else 0
            disk_total_gb = float(results.get('disk_total', 0)) if results.get('disk_total', '').replace('.', '').isdigit() else 0
            disk_used_gb = float(results.get('disk_used', 0)) if results.get('disk_used', '').replace('.', '').isdigit() else 0
            uptime_seconds = int(results.get('uptime', 0)) if results.get('uptime', '').isdigit() else 0

            # Parse load average
            load_avg = None
            if results.get('load_avg'):
                try:
                    load_avg = [float(x) for x in results['load_avg'].split()]
                except:
                    pass

            # Calculate percentages
            memory_percent = (memory_used_mb / memory_total_mb * 100) if memory_total_mb > 0 else 0
            disk_percent = (disk_used_gb / disk_total_gb * 100) if disk_total_gb > 0 else 0

            resources = ResourceUsage(
                cpu_percent=0,  # Can't easily get instant CPU % via SSH
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                memory_percent=memory_percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
                disk_percent=disk_percent,
                load_average=load_avg,
                uptime_seconds=uptime_seconds,
            )

            # Get network interfaces (simplified)
            interfaces = []
            try:
                stdin, stdout, stderr = ssh.exec_command('ip -j addr show')
                ip_json = stdout.read().decode('utf-8')
                ip_data = json.loads(ip_json)

                for iface in ip_data:
                    if_name = iface.get('ifname', '')
                    ip_address = None
                    mac_address = iface.get('address')

                    for addr_info in iface.get('addr_info', []):
                        if addr_info.get('family') == 'inet':
                            ip_address = addr_info.get('local')
                            break

                    interfaces.append(NetworkInterface(
                        name=if_name,
                        ip_address=ip_address,
                        mac_address=mac_address,
                        is_up='UP' in iface.get('flags', []),
                    ))
            except Exception as e:
                self.logger.warning(f"Failed to get network interfaces: {str(e)}")

            # Parse Docker versions
            docker_version = None
            if 'Docker version' in results.get('docker_version', ''):
                docker_version = results['docker_version']

            docker_compose_version = None
            if 'docker-compose' in results.get('docker_compose_version', '').lower():
                docker_compose_version = results['docker_compose_version']

            server = Server(
                name=server_config.name,
                hostname=server_config.hostname,
                role=ServerRole(server_config.role),
                criticality=Criticality(server_config.criticality),
                tailscale_ip=server_config.tailscale_ip,
                local_ip=server_config.local_ip,
                public_ip=getattr(server_config, 'public_ip', None),
                interfaces=interfaces,
                ssh=SSHConfig(**server_config.ssh.dict()) if server_config.ssh else None,
                os_name=results.get('os_name', ''),
                os_version=results.get('os_version', ''),
                kernel_version=results.get('kernel', ''),
                architecture=results.get('architecture', ''),
                cpu_model=results.get('cpu_model', ''),
                cpu_cores=cpu_cores,
                total_memory_gb=memory_total_mb / 1024,
                resources=resources,
                docker_version=docker_version,
                docker_compose_version=docker_compose_version,
                last_scanned=datetime.now(),
                reachable=True,
                notes=getattr(server_config, 'notes', None),
                purpose=getattr(server_config, 'purpose', None),
            )

            return server

        except Exception as e:
            self.add_error(f"Remote server scan failed for {server_config.name}: {str(e)}")
            raise

        finally:
            if ssh:
                ssh.close()

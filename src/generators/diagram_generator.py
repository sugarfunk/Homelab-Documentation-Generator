"""Infrastructure diagram generator."""

import logging
from pathlib import Path
from typing import List, Optional
import graphviz

from ..models.infrastructure import InfrastructureSnapshot, Server, DockerService
from ..models.documentation import Diagram, DiagramFormat


class DiagramGenerator:
    """Generates visual diagrams of infrastructure."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize diagram generator.

        Args:
            output_dir: Output directory for diagrams
        """
        self.logger = logging.getLogger(__name__)

        if output_dir is None:
            output_dir = Path("./output/diagrams")

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_diagrams(
        self,
        snapshot: InfrastructureSnapshot,
        formats: Optional[List[str]] = None
    ) -> List[Diagram]:
        """Generate all diagrams.

        Args:
            snapshot: Infrastructure snapshot
            formats: Output formats (svg, png)

        Returns:
            List of generated diagrams
        """
        if formats is None:
            formats = ['svg', 'png']

        diagrams = []

        self.logger.info("Generating infrastructure topology diagram...")
        topology = self.generate_topology_diagram(snapshot, formats)
        if topology:
            diagrams.extend(topology)

        self.logger.info("Generating service dependency diagram...")
        dependencies = self.generate_dependency_diagram(snapshot, formats)
        if dependencies:
            diagrams.extend(dependencies)

        self.logger.info(f"Generated {len(diagrams)} diagrams")

        return diagrams

    def generate_topology_diagram(
        self,
        snapshot: InfrastructureSnapshot,
        formats: List[str]
    ) -> List[Diagram]:
        """Generate infrastructure topology diagram.

        Args:
            snapshot: Infrastructure snapshot
            formats: Output formats

        Returns:
            List of diagram objects
        """
        diagrams = []

        try:
            # Create directed graph
            dot = graphviz.Digraph(comment='Infrastructure Topology')
            dot.attr(rankdir='TB', bgcolor='white')
            dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')

            # Add servers
            with dot.subgraph(name='cluster_servers') as s:
                s.attr(label='Servers', style='filled', color='lightgrey')

                for server in snapshot.servers:
                    # Color by criticality
                    color = self._get_criticality_color(server.criticality.value)

                    label = f"{server.name}\\n{server.os_name or 'Unknown'}\\n{server.role.value}"
                    s.node(server.name, label, fillcolor=color, color='black')

            # Add services
            with dot.subgraph(name='cluster_services') as sv:
                sv.attr(label='Services', style='filled', color='lightblue')

                # Group services by server
                services_by_server = {}
                for service in snapshot.services:
                    if service.server not in services_by_server:
                        services_by_server[service.server] = []
                    services_by_server[service.server].append(service)

                for server_name, services in services_by_server.items():
                    # Create subgraph for each server's services
                    with sv.subgraph(name=f'cluster_{server_name}_services') as ss:
                        ss.attr(label=f'{server_name} Services')

                        for service in services[:10]:  # Limit to avoid clutter
                            color = self._get_criticality_color(service.criticality.value)
                            label = service.name
                            if service.url:
                                label += f"\\n{service.url}"

                            service_id = f"svc_{service.name}_{server_name}"
                            ss.node(service_id, label, fillcolor=color, shape='ellipse')

                            # Connect service to server
                            dot.edge(server_name, service_id, style='dashed')

            # Add reverse proxies
            for proxy_config in getattr(snapshot, 'reverse_proxies', []):
                proxy_id = f"proxy_{proxy_config.name}"
                dot.node(proxy_id, f"Reverse Proxy\\n{proxy_config.name}",
                        fillcolor='orange', shape='diamond')

                # Connect proxy to server
                if hasattr(proxy_config, 'server'):
                    dot.edge(proxy_id, proxy_config.server, label='routes to')

            # Render to all formats
            for fmt in formats:
                output_file = self.output_dir / f"topology.{fmt}"
                dot.render(str(self.output_dir / "topology"), format=fmt, cleanup=True)

                diagrams.append(Diagram(
                    title="Infrastructure Topology",
                    type="topology",
                    format=DiagramFormat(fmt),
                    file_path=str(output_file),
                    description="Visual representation of servers, services, and their relationships"
                ))

            return diagrams

        except Exception as e:
            self.logger.error(f"Failed to generate topology diagram: {e}")
            return []

    def generate_dependency_diagram(
        self,
        snapshot: InfrastructureSnapshot,
        formats: List[str]
    ) -> List[Diagram]:
        """Generate service dependency diagram.

        Args:
            snapshot: Infrastructure snapshot
            formats: Output formats

        Returns:
            List of diagram objects
        """
        diagrams = []

        try:
            # Create directed graph
            dot = graphviz.Digraph(comment='Service Dependencies')
            dot.attr(rankdir='LR', bgcolor='white')
            dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')

            # Add all services
            for service in snapshot.services:
                color = self._get_criticality_color(service.criticality.value)
                label = f"{service.name}\\n({service.server})"

                dot.node(service.name, label, fillcolor=color)

                # Add dependency edges
                for dependency in service.depends_on:
                    dot.edge(service.name, dependency, color='blue')

                # Add reverse dependency edges
                for rev_dep in service.required_by:
                    dot.edge(rev_dep, service.name, color='red', style='dashed')

            # Render to all formats
            for fmt in formats:
                output_file = self.output_dir / f"dependencies.{fmt}"
                dot.render(str(self.output_dir / "dependencies"), format=fmt, cleanup=True)

                diagrams.append(Diagram(
                    title="Service Dependencies",
                    type="dependencies",
                    format=DiagramFormat(fmt),
                    file_path=str(output_file),
                    description="Service dependency relationships"
                ))

            return diagrams

        except Exception as e:
            self.logger.error(f"Failed to generate dependency diagram: {e}")
            return []

    def generate_network_diagram(
        self,
        snapshot: InfrastructureSnapshot,
        formats: List[str]
    ) -> List[Diagram]:
        """Generate network architecture diagram.

        Args:
            snapshot: Infrastructure snapshot
            formats: Output formats

        Returns:
            List of diagram objects
        """
        diagrams = []

        try:
            # Create graph
            dot = graphviz.Graph(comment='Network Architecture')
            dot.attr(bgcolor='white')
            dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')

            # Add internet
            dot.node('internet', 'Internet', fillcolor='lightblue', shape='cloud')

            # Add Tailscale network
            with dot.subgraph(name='cluster_tailscale') as ts:
                ts.attr(label='Tailscale VPN', style='filled', color='lightgreen')

                for server in snapshot.servers:
                    if server.tailscale_ip:
                        ts.node(f"ts_{server.name}", f"{server.name}\\n{server.tailscale_ip}",
                               fillcolor='white')

            # Connect internet to servers with public IPs
            for server in snapshot.servers:
                if server.public_ip:
                    dot.edge('internet', server.name, label=server.public_ip)

            # Render to all formats
            for fmt in formats:
                output_file = self.output_dir / f"network.{fmt}"
                dot.render(str(self.output_dir / "network"), format=fmt, cleanup=True)

                diagrams.append(Diagram(
                    title="Network Architecture",
                    type="network",
                    format=DiagramFormat(fmt),
                    file_path=str(output_file),
                    description="Network topology and connections"
                ))

            return diagrams

        except Exception as e:
            self.logger.error(f"Failed to generate network diagram: {e}")
            return []

    def _get_criticality_color(self, criticality: str) -> str:
        """Get color for criticality level.

        Args:
            criticality: Criticality level

        Returns:
            Color hex code
        """
        colors = {
            'critical': '#fee2e2',  # Light red
            'important': '#fef3c7',  # Light yellow
            'nice-to-have': '#d1fae5',  # Light green
        }
        return colors.get(criticality, '#f3f4f6')

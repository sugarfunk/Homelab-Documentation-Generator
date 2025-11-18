"""Infrastructure change detection."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .models.infrastructure import InfrastructureSnapshot


@dataclass
class Change:
    """Represents a detected change in infrastructure."""
    type: str  # server_added, server_removed, service_added, service_removed, config_changed, version_updated
    category: str  # servers, services, containers, network
    description: str
    details: Dict[str, Any]
    severity: str  # info, warning, critical
    timestamp: datetime


class ChangeDetector:
    """Detects changes between infrastructure snapshots."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize change detector.

        Args:
            data_dir: Directory to store snapshots
        """
        self.logger = logging.getLogger(__name__)

        if data_dir is None:
            data_dir = Path("./data/snapshots")

        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: InfrastructureSnapshot) -> Path:
        """Save snapshot for comparison.

        Args:
            snapshot: Snapshot to save

        Returns:
            Path to saved snapshot
        """
        timestamp_str = snapshot.timestamp.strftime('%Y%m%d-%H%M%S')
        snapshot_path = self.data_dir / f"snapshot-{timestamp_str}.json"

        with open(snapshot_path, 'w') as f:
            json.dump(snapshot.dict(), f, indent=2, default=str)

        # Also save as latest
        latest_path = self.data_dir / "snapshot-latest.json"
        with open(latest_path, 'w') as f:
            json.dump(snapshot.dict(), f, indent=2, default=str)

        self.logger.info(f"Snapshot saved: {snapshot_path}")

        return snapshot_path

    def load_latest_snapshot(self) -> Optional[InfrastructureSnapshot]:
        """Load the latest saved snapshot.

        Returns:
            Latest snapshot or None if not found
        """
        latest_path = self.data_dir / "snapshot-latest.json"

        if not latest_path.exists():
            return None

        try:
            with open(latest_path, 'r') as f:
                data = json.load(f)
                return InfrastructureSnapshot(**data)
        except Exception as e:
            self.logger.error(f"Failed to load latest snapshot: {e}")
            return None

    def detect_changes(
        self,
        current: InfrastructureSnapshot,
        previous: Optional[InfrastructureSnapshot] = None
    ) -> List[Change]:
        """Detect changes between snapshots.

        Args:
            current: Current snapshot
            previous: Previous snapshot (loads latest if None)

        Returns:
            List of detected changes
        """
        if previous is None:
            previous = self.load_latest_snapshot()

        if previous is None:
            self.logger.info("No previous snapshot found, this is the first scan")
            return []

        changes = []

        # Detect server changes
        changes.extend(self._detect_server_changes(current, previous))

        # Detect service changes
        changes.extend(self._detect_service_changes(current, previous))

        # Detect container changes
        changes.extend(self._detect_container_changes(current, previous))

        self.logger.info(f"Detected {len(changes)} changes")

        return changes

    def _detect_server_changes(
        self,
        current: InfrastructureSnapshot,
        previous: InfrastructureSnapshot
    ) -> List[Change]:
        """Detect changes in servers."""
        changes = []

        current_servers = {s.name: s for s in current.servers}
        previous_servers = {s.name: s for s in previous.servers}

        # Find added servers
        for name in current_servers.keys() - previous_servers.keys():
            changes.append(Change(
                type="server_added",
                category="servers",
                description=f"New server added: {name}",
                details={"server_name": name},
                severity="info",
                timestamp=datetime.now()
            ))

        # Find removed servers
        for name in previous_servers.keys() - current_servers.keys():
            changes.append(Change(
                type="server_removed",
                category="servers",
                description=f"Server removed: {name}",
                details={"server_name": name},
                severity="warning",
                timestamp=datetime.now()
            ))

        # Find changed servers
        for name in current_servers.keys() & previous_servers.keys():
            current_server = current_servers[name]
            previous_server = previous_servers[name]

            # Check for version changes
            if current_server.os_version != previous_server.os_version:
                changes.append(Change(
                    type="version_updated",
                    category="servers",
                    description=f"OS version changed on {name}: {previous_server.os_version} → {current_server.os_version}",
                    details={
                        "server_name": name,
                        "old_version": previous_server.os_version,
                        "new_version": current_server.os_version
                    },
                    severity="info",
                    timestamp=datetime.now()
                ))

            if current_server.docker_version != previous_server.docker_version:
                changes.append(Change(
                    type="version_updated",
                    category="servers",
                    description=f"Docker version changed on {name}",
                    details={
                        "server_name": name,
                        "old_version": previous_server.docker_version,
                        "new_version": current_server.docker_version
                    },
                    severity="info",
                    timestamp=datetime.now()
                ))

        return changes

    def _detect_service_changes(
        self,
        current: InfrastructureSnapshot,
        previous: InfrastructureSnapshot
    ) -> List[Change]:
        """Detect changes in services."""
        changes = []

        current_services = {s.name: s for s in current.services}
        previous_services = {s.name: s for s in previous.services}

        # Find added services
        for name in current_services.keys() - previous_services.keys():
            service = current_services[name]
            severity = "critical" if service.criticality.value == "critical" else "info"

            changes.append(Change(
                type="service_added",
                category="services",
                description=f"New service added: {name}",
                details={
                    "service_name": name,
                    "server": service.server,
                    "criticality": service.criticality.value
                },
                severity=severity,
                timestamp=datetime.now()
            ))

        # Find removed services
        for name in previous_services.keys() - current_services.keys():
            service = previous_services[name]
            severity = "critical" if service.criticality.value == "critical" else "warning"

            changes.append(Change(
                type="service_removed",
                category="services",
                description=f"Service removed: {name}",
                details={
                    "service_name": name,
                    "server": service.server,
                    "criticality": service.criticality.value
                },
                severity=severity,
                timestamp=datetime.now()
            ))

        # Find changed services
        for name in current_services.keys() & previous_services.keys():
            current_service = current_services[name]
            previous_service = previous_services[name]

            # Check for version changes
            if current_service.version != previous_service.version:
                changes.append(Change(
                    type="version_updated",
                    category="services",
                    description=f"Service {name} updated: {previous_service.version} → {current_service.version}",
                    details={
                        "service_name": name,
                        "old_version": previous_service.version,
                        "new_version": current_service.version
                    },
                    severity="info",
                    timestamp=datetime.now()
                ))

        return changes

    def _detect_container_changes(
        self,
        current: InfrastructureSnapshot,
        previous: InfrastructureSnapshot
    ) -> List[Change]:
        """Detect changes in containers."""
        changes = []

        current_count = current.total_containers
        previous_count = previous.total_containers

        if current_count != previous_count:
            changes.append(Change(
                type="container_count_changed",
                category="containers",
                description=f"Container count changed: {previous_count} → {current_count}",
                details={
                    "previous_count": previous_count,
                    "current_count": current_count,
                    "difference": current_count - previous_count
                },
                severity="info" if abs(current_count - previous_count) < 5 else "warning",
                timestamp=datetime.now()
            ))

        # Check running containers
        current_running = current.running_containers
        previous_running = previous.running_containers

        if current_running < previous_running:
            changes.append(Change(
                type="containers_stopped",
                category="containers",
                description=f"Running containers decreased: {previous_running} → {current_running}",
                details={
                    "previous_running": previous_running,
                    "current_running": current_running
                },
                severity="warning",
                timestamp=datetime.now()
            ))

        return changes

    def get_change_summary(self, changes: List[Change]) -> Dict[str, Any]:
        """Get summary of changes.

        Args:
            changes: List of changes

        Returns:
            Summary dictionary
        """
        return {
            "total_changes": len(changes),
            "by_category": self._group_by(changes, "category"),
            "by_type": self._group_by(changes, "type"),
            "by_severity": self._group_by(changes, "severity"),
            "critical_changes": [c for c in changes if c.severity == "critical"],
            "warnings": [c for c in changes if c.severity == "warning"],
        }

    def _group_by(self, changes: List[Change], field: str) -> Dict[str, int]:
        """Group changes by a field."""
        groups = {}
        for change in changes:
            key = getattr(change, field)
            groups[key] = groups.get(key, 0) + 1
        return groups

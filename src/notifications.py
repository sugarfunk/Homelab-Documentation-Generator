"""Notification system for infrastructure changes."""

import logging
import httpx
from typing import List, Optional
from datetime import datetime

from .change_detector import Change


class NTFYNotifier:
    """Send notifications via NTFY."""

    def __init__(self, config):
        """Initialize NTFY notifier.

        Args:
            config: Configuration object
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        ntfy_config = config.notifications.ntfy
        self.enabled = ntfy_config.get("enabled", False)
        self.server = ntfy_config.get("server", "https://ntfy.sh")
        self.topic = ntfy_config.get("topic", "homelab-docs")
        self.priority = ntfy_config.get("priority", "default")

    async def send_notification(
        self,
        title: str,
        message: str,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Send a notification.

        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (min, low, default, high, urgent)
            tags: List of tags/emojis

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            self.logger.debug("NTFY notifications disabled")
            return False

        try:
            headers = {
                "Title": title,
                "Priority": priority or self.priority,
            }

            if tags:
                headers["Tags"] = ",".join(tags)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server}/{self.topic}",
                    data=message.encode('utf-8'),
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    self.logger.info(f"Notification sent: {title}")
                    return True
                else:
                    self.logger.error(f"Failed to send notification: {response.status_code}")
                    return False

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False

    async def notify_scan_complete(
        self,
        servers: int,
        services: int,
        containers: int,
        duration: float
    ):
        """Send notification for completed scan.

        Args:
            servers: Number of servers scanned
            services: Number of services found
            containers: Number of containers found
            duration: Scan duration in seconds
        """
        if not self._should_notify("scan_complete"):
            return

        await self.send_notification(
            title="📊 Scan Complete",
            message=f"Infrastructure scan finished in {duration:.1f}s\n\n"
                   f"Found:\n"
                   f"• {servers} servers\n"
                   f"• {services} services\n"
                   f"• {containers} containers",
            priority="low",
            tags=["white_check_mark"]
        )

    async def notify_changes_detected(self, changes: List[Change]):
        """Send notification for detected changes.

        Args:
            changes: List of detected changes
        """
        if not self._should_notify("changes_detected"):
            return

        if not changes:
            return

        # Group by severity
        critical = [c for c in changes if c.severity == "critical"]
        warnings = [c for c in changes if c.severity == "warning"]
        info = [c for c in changes if c.severity == "info"]

        # Determine priority
        if critical:
            priority = "urgent"
            tags = ["rotating_light"]
        elif warnings:
            priority = "high"
            tags = ["warning"]
        else:
            priority = "default"
            tags = ["information_source"]

        # Build message
        message = f"{len(changes)} infrastructure changes detected:\n\n"

        if critical:
            message += f"🚨 {len(critical)} Critical:\n"
            for change in critical[:3]:  # Limit to avoid long messages
                message += f"  • {change.description}\n"
            if len(critical) > 3:
                message += f"  ... and {len(critical) - 3} more\n"
            message += "\n"

        if warnings:
            message += f"⚠️ {len(warnings)} Warnings:\n"
            for change in warnings[:3]:
                message += f"  • {change.description}\n"
            if len(warnings) > 3:
                message += f"  ... and {len(warnings) - 3} more\n"
            message += "\n"

        if info:
            message += f"ℹ️ {len(info)} Info:\n"
            for change in info[:2]:
                message += f"  • {change.description}\n"
            if len(info) > 2:
                message += f"  ... and {len(info) - 2} more\n"

        await self.send_notification(
            title=f"🔄 {len(changes)} Changes Detected",
            message=message,
            priority=priority,
            tags=tags
        )

    async def notify_errors(self, errors: List[str]):
        """Send notification for errors.

        Args:
            errors: List of error messages
        """
        if not self._should_notify("errors"):
            return

        if not errors:
            return

        message = f"{len(errors)} errors during scan:\n\n"
        for error in errors[:5]:  # Limit to 5 errors
            message += f"• {error}\n"

        if len(errors) > 5:
            message += f"\n... and {len(errors) - 5} more"

        await self.send_notification(
            title=f"❌ Scan Errors ({len(errors)})",
            message=message,
            priority="high",
            tags=["x"]
        )

    async def notify_weekly_summary(
        self,
        total_scans: int,
        total_changes: int,
        server_count: int,
        service_count: int
    ):
        """Send weekly summary notification.

        Args:
            total_scans: Number of scans this week
            total_changes: Number of changes detected
            server_count: Current server count
            service_count: Current service count
        """
        if not self._should_notify("weekly_summary"):
            return

        message = f"📈 Weekly Infrastructure Summary\n\n"
        message += f"Scans: {total_scans}\n"
        message += f"Changes: {total_changes}\n"
        message += f"Servers: {server_count}\n"
        message += f"Services: {service_count}\n\n"
        message += f"All systems documented and monitored!"

        await self.send_notification(
            title="📊 Weekly Summary",
            message=message,
            priority="low",
            tags=["bar_chart"]
        )

    def _should_notify(self, trigger: str) -> bool:
        """Check if notification should be sent for trigger.

        Args:
            trigger: Trigger name

        Returns:
            True if should notify
        """
        if not self.enabled:
            return False

        triggers = self.config.notifications.triggers
        return trigger in triggers

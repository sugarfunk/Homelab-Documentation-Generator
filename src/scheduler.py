"""Scheduled scanning functionality."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from croniter import croniter

from .utils.config import Config
from .scanner_orchestrator import ScannerOrchestrator
from .generators.doc_generator import DocumentationGenerator
from .generators.diagram_generator import DiagramGenerator
from .generators.output_formats import OutputFormatOrchestrator
from .change_detector import ChangeDetector
from .notifications import NTFYNotifier


class ScheduledScanner:
    """Handles scheduled infrastructure scanning."""

    def __init__(self, config: Config):
        """Initialize scheduled scanner.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get schedule from config
        self.schedule = config.scanning.schedule  # Cron format

        # Initialize components
        self.scanner = ScannerOrchestrator(config)
        self.doc_generator = DocumentationGenerator(config)
        self.diagram_generator = DiagramGenerator()
        self.output_orchestrator = OutputFormatOrchestrator(
            output_base_dir=Path(config.documentation.output_dir)
        )
        self.change_detector = ChangeDetector()
        self.notifier = NTFYNotifier(config)

        self.running = False

    async def run_scheduled_scan(self):
        """Run a scheduled scan with full documentation generation."""
        self.logger.info("Starting scheduled scan...")
        start_time = datetime.now()

        try:
            # Scan infrastructure
            self.logger.info("Scanning infrastructure...")
            snapshot = await self.scanner.scan_all()

            # Detect changes
            self.logger.info("Detecting changes...")
            changes = self.change_detector.detect_changes(snapshot)

            if changes:
                self.logger.info(f"Detected {len(changes)} changes")
                change_summary = self.change_detector.get_change_summary(changes)

                # Send notification about changes
                await self.notifier.notify_changes_detected(changes)
            else:
                self.logger.info("No changes detected")

            # Save snapshot
            self.change_detector.save_snapshot(snapshot)

            # Generate documentation
            if self.config.documentation.sections.get("auto_generate", True):
                self.logger.info("Generating documentation...")

                bundle = await self.doc_generator.generate_full_documentation(
                    snapshot,
                    enable_ai=self.config.llm.features.service_explanations
                )

                # Save bundle
                await self.doc_generator.save_bundle(bundle)

                # Generate diagrams
                diagrams = self.diagram_generator.generate_all_diagrams(snapshot)
                bundle.diagrams = diagrams

                # Generate output formats
                await self.output_orchestrator.generate_all(
                    bundle,
                    self.config.documentation.formats
                )

                self.logger.info("Documentation generation complete")

            # Send completion notification
            duration = (datetime.now() - start_time).total_seconds()
            await self.notifier.notify_scan_complete(
                servers=snapshot.total_servers,
                services=snapshot.total_services,
                containers=snapshot.total_containers,
                duration=duration
            )

            # Send error notification if any errors occurred
            if snapshot.scan_errors:
                await self.notifier.notify_errors(snapshot.scan_errors)

            self.logger.info(f"Scheduled scan completed in {duration:.2f}s")

        except Exception as e:
            self.logger.error(f"Scheduled scan failed: {e}")
            await self.notifier.notify_errors([str(e)])

    async def run_forever(self):
        """Run scanner on schedule forever."""
        self.running = True
        self.logger.info(f"Starting scheduled scanner with cron: {self.schedule}")

        cron = croniter(self.schedule, datetime.now())

        while self.running:
            # Get next run time
            next_run = cron.get_next(datetime)
            self.logger.info(f"Next scan scheduled for: {next_run}")

            # Wait until next run
            wait_seconds = (next_run - datetime.now()).total_seconds()

            if wait_seconds > 0:
                try:
                    await asyncio.sleep(wait_seconds)
                except asyncio.CancelledError:
                    self.logger.info("Scheduled scanner cancelled")
                    break

            # Run scan
            if self.running:
                await self.run_scheduled_scan()

    def stop(self):
        """Stop the scheduled scanner."""
        self.logger.info("Stopping scheduled scanner...")
        self.running = False


async def main():
    """Run scheduled scanner as standalone process."""
    import sys
    from .utils.config import load_config
    from .utils.logging_config import setup_logging

    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        print("Please create a config.yaml file")
        sys.exit(1)

    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting scheduled scanner service...")

    # Create and run scheduler
    scheduler = ScheduledScanner(config)

    try:
        await scheduler.run_forever()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())

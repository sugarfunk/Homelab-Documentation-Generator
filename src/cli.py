"""Command-line interface for homelab documentation generator."""

import asyncio
import click
import json
import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from .utils.config import load_config
from .utils.logging_config import setup_logging
from .scanner_orchestrator import ScannerOrchestrator

console = Console()


@click.group()
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
@click.option('--log-level', '-l', default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, config, log_level):
    """Homelab Documentation Generator - Create comprehensive infrastructure documentation."""
    ctx.ensure_object(dict)

    try:
        # Load configuration
        ctx.obj['config'] = load_config(config)

        # Setup logging
        setup_logging(
            level=log_level,
            log_file=ctx.obj['config'].logging.file,
            log_format=ctx.obj['config'].logging.format
        )

        ctx.obj['logger'] = logging.getLogger(__name__)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("\n[yellow]Please create a config.yaml file:[/yellow]")
        console.print("  cp config.example.yaml config.yaml")
        console.print("  # Edit config.yaml with your infrastructure details")
        ctx.exit(1)
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {str(e)}")
        ctx.exit(1)


@cli.command()
@click.option('--output', '-o', help='Output file for scan results')
@click.pass_context
def scan(ctx, output):
    """Scan infrastructure and collect information."""
    config = ctx.obj['config']
    logger = ctx.obj['logger']

    console.print("\n[bold cyan]🔍 Homelab Infrastructure Scanner[/bold cyan]\n")

    async def run_scan():
        orchestrator = ScannerOrchestrator(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Scanning infrastructure...", total=None)

            snapshot = await orchestrator.scan_all()

            progress.update(task, description="[green]Scan complete!")

        return snapshot

    # Run async scan
    snapshot = asyncio.run(run_scan())

    # Display results
    console.print("\n[bold green]✓ Scan Complete![/bold green]\n")

    # Create summary table
    table = Table(title="Infrastructure Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Servers", str(snapshot.total_servers))
    table.add_row("Services", str(snapshot.total_services))
    table.add_row("Containers", str(snapshot.total_containers))
    table.add_row("Running Containers", str(snapshot.running_containers))
    table.add_row("Scan Duration", f"{snapshot.scan_duration_seconds:.2f}s")

    if snapshot.scan_errors:
        table.add_row("Errors", str(len(snapshot.scan_errors)), style="yellow")

    console.print(table)

    # Show servers
    if snapshot.servers:
        console.print("\n[bold]Servers Found:[/bold]")
        for server in snapshot.servers:
            status = "✓" if server.reachable else "✗"
            console.print(f"  {status} {server.name} - {server.os_name or 'Unknown OS'}")

    # Show services summary
    if snapshot.services:
        console.print(f"\n[bold]Services Found:[/bold] {len(snapshot.services)}")
        console.print(f"  Top services by criticality:")

        critical = [s for s in snapshot.services if s.criticality.value == "critical"]
        important = [s for s in snapshot.services if s.criticality.value == "important"]

        if critical:
            console.print(f"    [red]Critical:[/red] {len(critical)}")
        if important:
            console.print(f"    [yellow]Important:[/yellow] {len(important)}")

    # Save to file if requested
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(snapshot.dict(), f, indent=2, default=str)

        console.print(f"\n[green]Results saved to:[/green] {output}")

    # Show errors if any
    if snapshot.scan_errors:
        console.print("\n[yellow]⚠ Errors encountered during scan:[/yellow]")
        for error in snapshot.scan_errors[:5]:  # Show first 5
            console.print(f"  • {error}")
        if len(snapshot.scan_errors) > 5:
            console.print(f"  ... and {len(snapshot.scan_errors) - 5} more")


@cli.command()
@click.option('--scan-file', '-s', help='Use existing scan results')
@click.option('--output-dir', '-o', help='Output directory')
@click.option('--enable-ai/--no-ai', default=True, help='Enable AI-powered features')
@click.option('--formats', '-f', multiple=True, help='Output formats (html, pdf, markdown)')
@click.pass_context
def generate(ctx, scan_file, output_dir, enable_ai, formats):
    """Generate documentation from scan results."""
    config = ctx.obj['config']
    logger = ctx.obj['logger']

    console.print("\n[bold cyan]📚 Documentation Generator[/bold cyan]\n")

    # Import generators here to avoid circular imports
    from .scanner_orchestrator import ScannerOrchestrator
    from .generators.doc_generator import DocumentationGenerator
    from .generators.diagram_generator import DiagramGenerator
    from .generators.output_formats import OutputFormatOrchestrator

    async def run_generation():
        # Get or load snapshot
        if scan_file:
            console.print(f"[cyan]Loading scan results from:[/cyan] {scan_file}")
            with open(scan_file, 'r') as f:
                from .models.infrastructure import InfrastructureSnapshot
                snapshot_data = json.load(f)
                snapshot = InfrastructureSnapshot(**snapshot_data)
        else:
            console.print("[cyan]No scan file provided, running new scan...[/cyan]")
            orchestrator = ScannerOrchestrator(config)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Scanning infrastructure...", total=None)
                snapshot = await orchestrator.scan_all()
                progress.update(task, description="[green]Scan complete!")

        # Generate documentation
        doc_gen = DocumentationGenerator(config)

        console.print("\n[cyan]Generating comprehensive documentation...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Creating documentation bundle...", total=None)

            bundle = await doc_gen.generate_full_documentation(
                snapshot,
                enable_ai=enable_ai
            )

            progress.update(task, description="[green]Documentation bundle created!")

        # Save bundle
        bundle_path = await doc_gen.save_bundle(bundle)
        console.print(f"\n[green]✓ Documentation bundle saved:[/green] {bundle_path}")

        # Generate diagrams
        console.print("\n[cyan]Generating infrastructure diagrams...[/cyan]")
        diagram_gen = DiagramGenerator(
            output_dir=Path(output_dir) / "diagrams" if output_dir else None
        )

        diagrams = diagram_gen.generate_all_diagrams(snapshot, formats=['svg', 'png'])
        console.print(f"[green]✓ Generated {len(diagrams)} diagrams[/green]")

        # Add diagrams to bundle
        bundle.diagrams = diagrams

        # Generate output formats
        output_formats = list(formats) if formats else config.documentation.formats

        console.print(f"\n[cyan]Generating output formats:[/cyan] {', '.join(output_formats)}")

        output_orchestrator = OutputFormatOrchestrator(
            output_base_dir=Path(output_dir) if output_dir else Path(config.documentation.output_dir)
        )

        outputs = await output_orchestrator.generate_all(bundle, output_formats)

        # Display results
        console.print("\n[bold green]✓ Documentation Generation Complete![/bold green]\n")

        result_table = Table(title="Generated Files")
        result_table.add_column("Format", style="cyan")
        result_table.add_column("Location", style="green")

        for fmt, path in outputs.items():
            result_table.add_row(fmt.upper(), str(path))

        console.print(result_table)

        # Show key files
        console.print("\n[bold]📁 Key Files:[/bold]")

        if 'html' in outputs:
            html_path = outputs['html']
            console.print(f"  • HTML Site: [green]{html_path}/index.html[/green]")
            console.print(f"  • Emergency Guide: [red]{html_path}/EMERGENCY_START_HERE.html[/red]")

        if 'markdown' in outputs:
            md_path = outputs['markdown']
            console.print(f"  • Markdown: [green]{md_path}/README.md[/green]")

        if 'pdf' in outputs:
            console.print(f"  • PDF: [green]{outputs['pdf']}[/green]")

        if diagrams:
            console.print(f"  • Diagrams: [green]{diagrams[0].file_path.rsplit('/', 1)[0]}[/green]")

        console.print("\n[bold cyan]🎉 Your homelab documentation is ready![/bold cyan]")

        return bundle

    # Run async generation
    bundle = asyncio.run(run_generation())


@cli.command()
@click.pass_context
def info(ctx):
    """Show configuration information."""
    config = ctx.obj['config']

    console.print("\n[bold cyan]Configuration Information[/bold cyan]\n")

    # Servers
    table = Table(title="Configured Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Hostname", style="white")
    table.add_column("Role", style="green")
    table.add_column("Criticality", style="yellow")

    for server in config.infrastructure.servers:
        table.add_row(
            server.name,
            server.hostname,
            server.role,
            server.criticality
        )

    console.print(table)

    # Scanners
    console.print(f"\n[bold]Enabled Scanners:[/bold]")
    for scanner in config.scanning.enabled_scanners:
        console.print(f"  ✓ {scanner}")

    # LLM
    console.print(f"\n[bold]LLM Configuration:[/bold]")
    console.print(f"  Default Provider: {config.llm.default_provider}")
    console.print(f"  Privacy Mode: {'Enabled' if config.llm.privacy_mode else 'Disabled'}")

    # Output
    console.print(f"\n[bold]Output:[/bold]")
    console.print(f"  Directory: {config.documentation.output_dir}")
    console.print(f"  Formats: {', '.join(config.documentation.formats)}")


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate configuration."""
    config = ctx.obj['config']

    console.print("\n[bold cyan]🔍 Configuration Validation[/bold cyan]\n")

    issues = []

    # Check servers
    if not config.infrastructure.servers:
        issues.append("No servers configured")

    # Check LLM configuration
    if config.llm.features.service_explanations:
        provider = config.llm.providers.get(config.llm.default_provider)
        if not provider:
            issues.append(f"LLM provider '{config.llm.default_provider}' not configured")

    # Check output directory
    output_dir = Path(config.documentation.output_dir)
    if not output_dir.exists():
        console.print(f"[yellow]Output directory will be created:[/yellow] {output_dir}")

    if issues:
        console.print("[red]Configuration Issues Found:[/red]")
        for issue in issues:
            console.print(f"  ✗ {issue}")
        return

    console.print("[green]✓ Configuration is valid![/green]")


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, type=int, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
@click.pass_context
def serve(ctx, host, port, reload):
    """Start the web interface."""
    import uvicorn
    from .web.app import create_app

    console.print("\n[bold cyan]🌐 Starting Web Interface[/bold cyan]\n")
    console.print(f"[green]Server starting at:[/green] http://{host}:{port}")
    console.print("\n[bold]Features:[/bold]")
    console.print("  • Browse documentation")
    console.print("  • Trigger scans via API")
    console.print("  • View infrastructure status")
    console.print("  • RESTful API")
    console.print("\n[cyan]Press Ctrl+C to stop[/cyan]\n")

    # Create and run app
    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload
    )


@cli.command()
@click.pass_context
def scheduler(ctx):
    """Run scheduled scanner service."""
    from .scheduler import ScheduledScanner

    config = ctx.obj['config']

    console.print("\n[bold cyan]⏰ Scheduled Scanner Service[/bold cyan]\n")
    console.print(f"[cyan]Schedule:[/cyan] {config.scanning.schedule}")
    console.print("\n[bold]This will:[/bold]")
    console.print("  • Run infrastructure scans on schedule")
    console.print("  • Detect changes automatically")
    console.print("  • Generate documentation")
    console.print("  • Send NTFY notifications")
    console.print("\n[cyan]Press Ctrl+C to stop[/cyan]\n")

    async def run():
        scheduler_service = ScheduledScanner(config)
        try:
            await scheduler_service.run_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping scheduler...[/yellow]")
            scheduler_service.stop()

    asyncio.run(run())


@cli.command()
@click.option('--scan-file', '-s', help='Snapshot file to analyze')
@click.pass_context
def changes(ctx, scan_file):
    """Detect changes since last scan."""
    from .change_detector import ChangeDetector

    console.print("\n[bold cyan]🔄 Change Detection[/bold cyan]\n")

    change_detector = ChangeDetector()

    if scan_file:
        # Load specified snapshot
        with open(scan_file, 'r') as f:
            from .models.infrastructure import InfrastructureSnapshot
            snapshot_data = json.load(f)
            current = InfrastructureSnapshot(**snapshot_data)
    else:
        # Load latest
        current = change_detector.load_latest_snapshot()

        if current is None:
            console.print("[yellow]No snapshots found. Run a scan first.[/yellow]")
            return

    # Detect changes
    detected_changes = change_detector.detect_changes(current)

    if not detected_changes:
        console.print("[green]✓ No changes detected since last scan[/green]")
        return

    # Show changes
    console.print(f"[bold]Found {len(detected_changes)} changes:[/bold]\n")

    # Group by severity
    critical = [c for c in detected_changes if c.severity == "critical"]
    warnings = [c for c in detected_changes if c.severity == "warning"]
    info = [c for c in detected_changes if c.severity == "info"]

    if critical:
        console.print(f"[bold red]🚨 Critical ({len(critical)}):[/bold red]")
        for change in critical:
            console.print(f"  • {change.description}")
        console.print()

    if warnings:
        console.print(f"[bold yellow]⚠️  Warnings ({len(warnings)}):[/bold yellow]")
        for change in warnings:
            console.print(f"  • {change.description}")
        console.print()

    if info:
        console.print(f"[bold cyan]ℹ️  Info ({len(info)}):[/bold cyan]")
        for change in info:
            console.print(f"  • {change.description}")


if __name__ == '__main__':
    cli(obj={})

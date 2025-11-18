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
@click.pass_context
def generate(ctx, scan_file, output_dir):
    """Generate documentation from scan results."""
    config = ctx.obj['config']

    console.print("\n[bold cyan]📚 Documentation Generator[/bold cyan]\n")
    console.print("[yellow]Full documentation generation coming soon![/yellow]")
    console.print("\nThis will generate:")
    console.print("  • HTML documentation site")
    console.print("  • PDF export")
    console.print("  • Markdown files")
    console.print("  • Infrastructure diagrams")
    console.print("  • Emergency guide")
    console.print("  • Quick reference cards")


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
@click.pass_context
def serve(ctx, host, port):
    """Start the web interface."""
    console.print("\n[bold cyan]🌐 Starting Web Interface[/bold cyan]\n")
    console.print(f"[green]Server will start at:[/green] http://{host}:{port}")
    console.print("\n[yellow]Web interface coming soon![/yellow]")
    console.print("\nThe web interface will provide:")
    console.print("  • Browse documentation")
    console.print("  • Trigger scans")
    console.print("  • View change history")
    console.print("  • Download exports")


if __name__ == '__main__':
    cli(obj={})

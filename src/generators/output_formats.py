"""Output format generators for documentation."""

import logging
from pathlib import Path
from typing import Optional
import json
import subprocess

from ..models.documentation import DocumentationBundle, DocumentationMode
from .html_generator import HTMLGenerator


class MarkdownGenerator:
    """Generates Markdown documentation."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize markdown generator.

        Args:
            output_dir: Output directory
        """
        self.logger = logging.getLogger(__name__)

        if output_dir is None:
            output_dir = Path("./output/markdown")

        self.output_dir = output_dir

    async def generate(
        self,
        bundle: DocumentationBundle,
        mode: DocumentationMode = DocumentationMode.TECHNICAL
    ) -> Path:
        """Generate Markdown documentation.

        Args:
            bundle: Documentation bundle
            mode: Documentation mode

        Returns:
            Path to generated documentation
        """
        self.logger.info(f"Generating Markdown documentation...")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate README.md
        readme_path = self.output_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(self._generate_readme(bundle))

        # Generate server files
        servers_dir = self.output_dir / "servers"
        servers_dir.mkdir(exist_ok=True)

        for server in bundle.servers:
            server_path = servers_dir / f"{server.server_name}.md"
            with open(server_path, 'w') as f:
                f.write(self._generate_server_md(server))

        # Generate service files
        services_dir = self.output_dir / "services"
        services_dir.mkdir(exist_ok=True)

        for service in bundle.services:
            service_path = services_dir / f"{service.service_name}.md"
            with open(service_path, 'w') as f:
                f.write(self._generate_service_md(service))

        # Generate emergency guide
        if bundle.emergency:
            emergency_path = self.output_dir / "EMERGENCY_START_HERE.md"
            with open(emergency_path, 'w') as f:
                f.write(self._generate_emergency_md(bundle.emergency))

        self.logger.info(f"Markdown documentation generated at: {self.output_dir}")

        return self.output_dir

    def _generate_readme(self, bundle: DocumentationBundle) -> str:
        """Generate main README."""
        md = f"""# Homelab Infrastructure Documentation

Generated: {bundle.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Overview

{bundle.infrastructure_summary}

## Quick Links

- [Emergency Guide](EMERGENCY_START_HERE.md) 🚨
- [Servers](servers/)
- [Services](services/)

## Infrastructure Summary

- **Servers**: {bundle.infrastructure_summary.get('total_servers', 0)}
- **Services**: {bundle.infrastructure_summary.get('total_services', 0)}
- **Containers**: {bundle.infrastructure_summary.get('total_containers', 0)}
- **Running**: {bundle.infrastructure_summary.get('running_containers', 0)}

## Servers

"""
        for server in bundle.servers:
            md += f"- [{server.server_name}](servers/{server.server_name}.md) - {server.summary}\n"

        md += "\n## Services\n\n"

        for service in bundle.services:
            md += f"- [{service.service_name}](services/{service.service_name}.md) - {service.criticality}\n"

        return md

    def _generate_server_md(self, server) -> str:
        """Generate server markdown."""
        md = f"""# {server.server_name}

{server.summary}

**Criticality**: {server.criticality}

## Hardware

"""
        for key, value in server.hardware_specs.items():
            md += f"- **{key}**: {value}\n"

        md += "\n## Operating System\n\n"

        for key, value in server.os_info.items():
            md += f"- **{key}**: {value}\n"

        md += "\n## Network\n\n"

        for key, value in server.network_info.items():
            md += f"- **{key}**: {value}\n"

        if server.plain_english_summary:
            md += f"\n## In Simple Terms\n\n{server.plain_english_summary}\n"

        return md

    def _generate_service_md(self, service) -> str:
        """Generate service markdown."""
        md = f"""# {service.service_name}

{service.summary}

**Criticality**: {service.criticality}
**Server**: {service.server_location}

## Access

"""
        if service.access_url:
            md += f"- **URL**: {service.access_url}\n"

        if service.ports:
            md += f"- **Ports**: {', '.join(service.ports)}\n"

        md += f"- **Credentials**: {service.credential_location}\n"

        md += "\n## Technical Details\n\n"

        for key, value in service.docker_info.items():
            md += f"- **{key}**: {value}\n"

        if service.plain_english_summary:
            md += f"\n## In Simple Terms\n\n{service.plain_english_summary}\n"

        return md

    def _generate_emergency_md(self, emergency) -> str:
        """Generate emergency guide markdown."""
        md = f"""# 🚨 EMERGENCY START HERE

## Step 1: Access Password Manager

- **Type**: {emergency.password_manager_type}
- **URL**: {emergency.password_manager_url}
- **Emergency Access**: {emergency.password_manager_access}

## Critical Services

"""
        for service in emergency.critical_services:
            md += f"- **{service['name']}** on {service['server']}\n"

        md += "\n## Emergency Contacts\n\n"

        for contact in emergency.emergency_contacts:
            md += f"### {contact.name} - {contact.role}\n\n"
            if contact.phone:
                md += f"- Phone: {contact.phone}\n"
            if contact.email:
                md += f"- Email: {contact.email}\n"
            md += "\n"

        md += "## Immediate Actions\n\n"

        for i, action in enumerate(emergency.immediate_actions, 1):
            md += f"{i}. {action}\n"

        md += f"\n## {emergency.disaster_recovery.title}\n\n"
        md += f"{emergency.disaster_recovery.description}\n\n"

        for i, step in enumerate(emergency.disaster_recovery.steps, 1):
            md += f"{i}. {step}\n"

        return md


class PDFGenerator:
    """Generates PDF documentation."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize PDF generator.

        Args:
            output_dir: Output directory
        """
        self.logger = logging.getLogger(__name__)

        if output_dir is None:
            output_dir = Path("./output/pdf")

        self.output_dir = output_dir

    async def generate(
        self,
        bundle: DocumentationBundle,
        mode: DocumentationMode = DocumentationMode.TECHNICAL,
        html_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """Generate PDF documentation from HTML.

        Args:
            bundle: Documentation bundle
            mode: Documentation mode
            html_dir: Directory containing HTML files

        Returns:
            Path to generated PDF or None if failed
        """
        self.logger.info("Generating PDF documentation...")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # If HTML directory not provided, generate HTML first
        if html_dir is None:
            html_gen = HTMLGenerator()
            html_dir = await html_gen.generate(bundle, mode)

        output_pdf = self.output_dir / f"homelab-documentation-{bundle.generated_at.strftime('%Y%m%d')}.pdf"

        # Try using wkhtmltopdf if available (better quality)
        if self._has_wkhtmltopdf():
            return await self._generate_with_wkhtmltopdf(html_dir, output_pdf)

        # Fallback to WeasyPrint
        return await self._generate_with_weasyprint(html_dir, output_pdf)

    def _has_wkhtmltopdf(self) -> bool:
        """Check if wkhtmltopdf is available."""
        try:
            subprocess.run(['wkhtmltopdf', '--version'],
                         capture_output=True, check=True)
            return True
        except:
            return False

    async def _generate_with_wkhtmltopdf(
        self,
        html_dir: Path,
        output_pdf: Path
    ) -> Optional[Path]:
        """Generate PDF using wkhtmltopdf."""
        try:
            # Combine HTML files into single PDF
            index_html = html_dir / "index.html"

            if index_html.exists():
                subprocess.run([
                    'wkhtmltopdf',
                    '--enable-local-file-access',
                    '--print-media-type',
                    str(index_html),
                    str(output_pdf)
                ], check=True)

                self.logger.info(f"PDF generated: {output_pdf}")
                return output_pdf

        except Exception as e:
            self.logger.error(f"PDF generation with wkhtmltopdf failed: {e}")

        return None

    async def _generate_with_weasyprint(
        self,
        html_dir: Path,
        output_pdf: Path
    ) -> Optional[Path]:
        """Generate PDF using WeasyPrint."""
        try:
            from weasyprint import HTML

            index_html = html_dir / "index.html"

            if index_html.exists():
                HTML(str(index_html)).write_pdf(str(output_pdf))

                self.logger.info(f"PDF generated: {output_pdf}")
                return output_pdf

        except ImportError:
            self.logger.error("WeasyPrint not available. Install with: pip install weasyprint")
        except Exception as e:
            self.logger.error(f"PDF generation with WeasyPrint failed: {e}")

        return None


class OutputFormatOrchestrator:
    """Orchestrates generation of all output formats."""

    def __init__(self, output_base_dir: Optional[Path] = None):
        """Initialize orchestrator.

        Args:
            output_base_dir: Base output directory
        """
        self.logger = logging.getLogger(__name__)

        if output_base_dir is None:
            output_base_dir = Path("./output")

        self.output_base_dir = output_base_dir

        # Initialize generators
        self.html_gen = HTMLGenerator(
            output_dir=output_base_dir / "html"
        )
        self.markdown_gen = MarkdownGenerator(
            output_dir=output_base_dir / "markdown"
        )
        self.pdf_gen = PDFGenerator(
            output_dir=output_base_dir / "pdf"
        )

    async def generate_all(
        self,
        bundle: DocumentationBundle,
        formats: Optional[list] = None,
        mode: DocumentationMode = DocumentationMode.TECHNICAL
    ) -> dict:
        """Generate all requested output formats.

        Args:
            bundle: Documentation bundle
            formats: List of formats to generate (html, pdf, markdown)
            mode: Documentation mode

        Returns:
            Dictionary mapping format to output path
        """
        if formats is None:
            formats = ['html', 'pdf', 'markdown']

        outputs = {}

        if 'html' in formats:
            self.logger.info("Generating HTML...")
            html_path = await self.html_gen.generate(bundle, mode)
            outputs['html'] = html_path

        if 'markdown' in formats:
            self.logger.info("Generating Markdown...")
            md_path = await self.markdown_gen.generate(bundle, mode)
            outputs['markdown'] = md_path

        if 'pdf' in formats:
            self.logger.info("Generating PDF...")
            html_dir = outputs.get('html')
            pdf_path = await self.pdf_gen.generate(bundle, mode, html_dir)
            if pdf_path:
                outputs['pdf'] = pdf_path

        # Save output paths to bundle
        bundle.output_paths = {k: str(v) for k, v in outputs.items()}

        return outputs

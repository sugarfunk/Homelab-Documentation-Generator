"""HTML documentation generator."""

import logging
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import shutil

from ..models.documentation import DocumentationBundle, DocumentationMode


class HTMLGenerator:
    """Generates HTML documentation from documentation bundle."""

    def __init__(self, template_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """Initialize HTML generator.

        Args:
            template_dir: Directory containing Jinja2 templates
            output_dir: Output directory for generated HTML
        """
        self.logger = logging.getLogger(__name__)

        if template_dir is None:
            template_dir = Path(__file__).parent.parent.parent / "templates"

        if output_dir is None:
            output_dir = Path("./output/html")

        self.template_dir = template_dir
        self.output_dir = output_dir

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters['datetimeformat'] = self._datetime_format

    def _datetime_format(self, value, format='%Y-%m-%d %H:%M:%S'):
        """Format datetime for templates."""
        if value is None:
            return ""
        return value.strftime(format)

    async def generate(
        self,
        bundle: DocumentationBundle,
        mode: DocumentationMode = DocumentationMode.TECHNICAL
    ) -> Path:
        """Generate HTML documentation.

        Args:
            bundle: Documentation bundle
            mode: Documentation mode

        Returns:
            Path to generated documentation
        """
        self.logger.info(f"Generating HTML documentation in {mode.value} mode...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy static assets
        self._copy_static_assets()

        # Generate index page
        await self._generate_index(bundle, mode)

        # Generate server pages
        for server in bundle.servers:
            await self._generate_server_page(server, mode)

        # Generate service pages
        for service in bundle.services:
            await self._generate_service_page(service, mode)

        # Generate emergency guide
        if bundle.emergency:
            await self._generate_emergency_guide(bundle.emergency, mode)

        # Generate network documentation
        if bundle.network:
            await self._generate_network_page(bundle.network, mode)

        # Generate procedures page
        await self._generate_procedures_page(bundle.procedures, mode)

        # Generate glossary
        if bundle.glossary:
            await self._generate_glossary_page(bundle.glossary, mode)

        self.logger.info(f"HTML documentation generated at: {self.output_dir}")

        return self.output_dir

    def _copy_static_assets(self):
        """Copy static CSS, JS, and images."""
        static_source = Path(__file__).parent.parent.parent / "static"
        static_dest = self.output_dir / "static"

        if static_source.exists():
            if static_dest.exists():
                shutil.rmtree(static_dest)
            shutil.copytree(static_source, static_dest)
        else:
            # Create minimal static directory
            static_dest.mkdir(exist_ok=True)
            self._create_default_css(static_dest / "style.css")

    def _create_default_css(self, css_path: Path):
        """Create a default CSS file."""
        css_content = """
/* Homelab Documentation - Default Styles */
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --bg-color: #ffffff;
    --text-color: #1f2937;
    --border-color: #e5e7eb;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    background: var(--primary-color);
    color: white;
    padding: 20px 0;
    margin-bottom: 30px;
}

header h1 {
    font-size: 2em;
    margin-bottom: 5px;
}

nav {
    background: #f3f4f6;
    padding: 15px;
    margin-bottom: 30px;
    border-radius: 8px;
}

nav ul {
    list-style: none;
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}

nav a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
}

nav a:hover {
    text-decoration: underline;
}

.section {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.section h2 {
    color: var(--primary-color);
    margin-bottom: 15px;
    border-bottom: 2px solid var(--primary-color);
    padding-bottom: 10px;
}

.section h3 {
    color: var(--text-color);
    margin-top: 20px;
    margin-bottom: 10px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

th {
    background: #f9fafb;
    font-weight: 600;
}

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85em;
    font-weight: 600;
}

.badge-critical {
    background: #fee2e2;
    color: #991b1b;
}

.badge-important {
    background: #fef3c7;
    color: #92400e;
}

.badge-success {
    background: #d1fae5;
    color: #065f46;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.stat-card {
    background: #f9fafb;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid var(--primary-color);
}

.stat-card h3 {
    font-size: 0.9em;
    color: #6b7280;
    margin: 0 0 5px 0;
}

.stat-card .value {
    font-size: 2em;
    font-weight: bold;
    color: var(--primary-color);
}

.emergency-banner {
    background: #fee2e2;
    border: 2px solid #ef4444;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.emergency-banner h2 {
    color: #991b1b;
    margin: 0 0 10px 0;
}

.procedure {
    background: #f9fafb;
    border-left: 4px solid var(--primary-color);
    padding: 20px;
    margin: 20px 0;
}

.procedure ol {
    margin-left: 20px;
    margin-top: 10px;
}

.procedure li {
    margin: 8px 0;
}

code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
}

pre {
    background: #1f2937;
    color: #f9fafb;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 15px 0;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
}

.warning {
    background: #fef3c7;
    border-left: 4px solid #f59e0b;
    padding: 15px;
    margin: 15px 0;
}

.info {
    background: #dbeafe;
    border-left: 4px solid #2563eb;
    padding: 15px;
    margin: 15px 0;
}

footer {
    margin-top: 50px;
    padding: 20px 0;
    border-top: 1px solid var(--border-color);
    text-align: center;
    color: #6b7280;
}

@media (max-width: 768px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }

    nav ul {
        flex-direction: column;
        gap: 10px;
    }
}
"""
        css_path.write_text(css_content)

    async def _generate_index(self, bundle: DocumentationBundle, mode: DocumentationMode):
        """Generate index page."""
        template = self._get_or_create_template('index.html', self._default_index_template())

        context = {
            'bundle': bundle,
            'mode': mode,
            'title': 'Homelab Documentation',
        }

        output_path = self.output_dir / 'index.html'
        self._render_template(template, context, output_path)

    async def _generate_server_page(self, server, mode: DocumentationMode):
        """Generate server detail page."""
        template = self._get_or_create_template('server.html', self._default_server_template())

        context = {
            'server': server,
            'mode': mode,
            'title': f'Server: {server.server_name}',
        }

        output_path = self.output_dir / f'server-{server.server_name}.html'
        self._render_template(template, context, output_path)

    async def _generate_service_page(self, service, mode: DocumentationMode):
        """Generate service detail page."""
        template = self._get_or_create_template('service.html', self._default_service_template())

        context = {
            'service': service,
            'mode': mode,
            'title': f'Service: {service.service_name}',
        }

        output_path = self.output_dir / f'service-{service.service_name}.html'
        self._render_template(template, context, output_path)

    async def _generate_emergency_guide(self, emergency, mode: DocumentationMode):
        """Generate emergency guide."""
        template = self._get_or_create_template('emergency.html', self._default_emergency_template())

        context = {
            'emergency': emergency,
            'mode': mode,
            'title': 'EMERGENCY START HERE',
        }

        output_path = self.output_dir / 'EMERGENCY_START_HERE.html'
        self._render_template(template, context, output_path)

    async def _generate_network_page(self, network, mode: DocumentationMode):
        """Generate network documentation page."""
        template = self._get_or_create_template('network.html', self._default_network_template())

        context = {
            'network': network,
            'mode': mode,
            'title': 'Network Documentation',
        }

        output_path = self.output_dir / 'network.html'
        self._render_template(template, context, output_path)

    async def _generate_procedures_page(self, procedures, mode: DocumentationMode):
        """Generate procedures page."""
        template = self._get_or_create_template('procedures.html', self._default_procedures_template())

        context = {
            'procedures': procedures,
            'mode': mode,
            'title': 'Procedures',
        }

        output_path = self.output_dir / 'procedures.html'
        self._render_template(template, context, output_path)

    async def _generate_glossary_page(self, glossary, mode: DocumentationMode):
        """Generate glossary page."""
        template = self._get_or_create_template('glossary.html', self._default_glossary_template())

        context = {
            'glossary': glossary,
            'mode': mode,
            'title': 'Glossary',
        }

        output_path = self.output_dir / 'glossary.html'
        self._render_template(template, context, output_path)

    def _get_or_create_template(self, template_name: str, default_content: str):
        """Get template or create default if not exists."""
        template_path = self.template_dir / template_name

        if not template_path.exists():
            # Create template directory if needed
            self.template_dir.mkdir(parents=True, exist_ok=True)
            template_path.write_text(default_content)
            # Reload environment
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self.env.filters['datetimeformat'] = self._datetime_format

        return self.env.get_template(template_name)

    def _render_template(self, template, context, output_path: Path):
        """Render template to file."""
        html = template.render(**context)
        output_path.write_text(html)
        self.logger.debug(f"Generated: {output_path}")

    def _default_index_template(self) -> str:
        """Default index template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🏠 {{ title }}</h1>
            <p>Complete infrastructure documentation - Generated {{ bundle.generated_at|datetimeformat }}</p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="EMERGENCY_START_HERE.html" style="color: red; font-weight: bold;">🚨 EMERGENCY GUIDE</a></li>
                <li><a href="network.html">Network</a></li>
                <li><a href="procedures.html">Procedures</a></li>
                <li><a href="glossary.html">Glossary</a></li>
            </ul>
        </nav>

        <div class="section">
            <h2>📊 Infrastructure Overview</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Servers</h3>
                    <div class="value">{{ bundle.infrastructure_summary.total_servers }}</div>
                </div>
                <div class="stat-card">
                    <h3>Services</h3>
                    <div class="value">{{ bundle.infrastructure_summary.total_services }}</div>
                </div>
                <div class="stat-card">
                    <h3>Containers</h3>
                    <div class="value">{{ bundle.infrastructure_summary.total_containers }}</div>
                </div>
                <div class="stat-card">
                    <h3>Running</h3>
                    <div class="value">{{ bundle.infrastructure_summary.running_containers }}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🖥️ Servers</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>OS</th>
                        <th>Criticality</th>
                        <th>Services</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for server in bundle.servers %}
                    <tr>
                        <td><strong>{{ server.server_name }}</strong></td>
                        <td>{{ server.os_info.get('Operating System', 'Unknown') }}</td>
                        <td><span class="badge badge-{{ server.criticality }}">{{ server.criticality }}</span></td>
                        <td>{{ server.service_count }}</td>
                        <td><a href="server-{{ server.server_name }}.html">View Details →</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🐳 Services</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Server</th>
                        <th>Criticality</th>
                        <th>Access</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for service in bundle.services %}
                    <tr>
                        <td><strong>{{ service.service_name }}</strong></td>
                        <td>{{ service.server_location }}</td>
                        <td><span class="badge badge-{{ service.criticality }}">{{ service.criticality }}</span></td>
                        <td>{% if service.access_url %}<a href="{{ service.access_url }}" target="_blank">Open ↗</a>{% else %}N/A{% endif %}</td>
                        <td><a href="service-{{ service.service_name }}.html">View Details →</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <footer>
            <p>Last updated: {{ bundle.generated_at|datetimeformat }}</p>
            <p>Homelab Documentation Generator v{{ bundle.version }}</p>
        </footer>
    </div>
</body>
</html>'''

    def _default_server_template(self) -> str:
        """Default server template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🖥️ {{ server.server_name }}</h1>
            <p>{{ server.summary }}</p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">← Back to Home</a></li>
                <li><a href="EMERGENCY_START_HERE.html">🚨 Emergency Guide</a></li>
            </ul>
        </nav>

        {% if mode.value == 'non_technical' and server.plain_english_summary %}
        <div class="info">
            <h3>In Simple Terms:</h3>
            <p>{{ server.plain_english_summary }}</p>
        </div>
        {% endif %}

        <div class="section">
            <h2>Hardware Specifications</h2>
            <table>
                {% for key, value in server.hardware_specs.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div class="section">
            <h2>Operating System</h2>
            <table>
                {% for key, value in server.os_info.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div class="section">
            <h2>Network Information</h2>
            <table>
                {% for key, value in server.network_info.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        {% if server.resource_usage %}
        <div class="section">
            <h2>Resource Usage</h2>
            <table>
                {% for key, value in server.resource_usage.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}

        <footer>
            <p><a href="index.html">← Back to Home</a></p>
        </footer>
    </div>
</body>
</html>'''

    def _default_service_template(self) -> str:
        """Default service template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🐳 {{ service.service_name }}</h1>
            <p><span class="badge badge-{{ service.criticality }}">{{ service.criticality }}</span></p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">← Back to Home</a></li>
                <li><a href="server-{{ service.server_location }}.html">Server: {{ service.server_location }}</a></li>
            </ul>
        </nav>

        <div class="section">
            <h2>Overview</h2>
            <p>{{ service.summary }}</p>

            {% if mode.value == 'non_technical' and service.plain_english_summary %}
            <div class="info">
                <h3>In Simple Terms:</h3>
                <p>{{ service.plain_english_summary }}</p>
            </div>
            {% endif %}
        </div>

        <div class="section">
            <h2>Access Information</h2>
            <table>
                {% if service.access_url %}
                <tr>
                    <th>Access URL</th>
                    <td><a href="{{ service.access_url }}" target="_blank">{{ service.access_url }} ↗</a></td>
                </tr>
                {% endif %}
                {% if service.ports %}
                <tr>
                    <th>Ports</th>
                    <td>{{ service.ports|join(', ') }}</td>
                </tr>
                {% endif %}
                <tr>
                    <th>Credentials</th>
                    <td>{{ service.credential_location }}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Technical Details</h2>
            <table>
                <tr>
                    <th>Server</th>
                    <td><a href="server-{{ service.server_location }}.html">{{ service.server_location }}</a></td>
                </tr>
                {% for key, value in service.docker_info.items() %}
                <tr>
                    <th>{{ key }}</th>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        {% if service.dependencies or service.reverse_dependencies %}
        <div class="section">
            <h2>Dependencies</h2>
            {% if service.dependencies %}
            <h3>Depends On:</h3>
            <ul>
                {% for dep in service.dependencies %}
                <li>{{ dep }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            {% if service.reverse_dependencies %}
            <h3>Required By:</h3>
            <ul>
                {% for dep in service.reverse_dependencies %}
                <li>{{ dep }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endif %}

        <footer>
            <p><a href="index.html">← Back to Home</a></p>
        </footer>
    </div>
</body>
</html>'''

    def _default_emergency_template(self) -> str:
        """Default emergency guide template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header style="background: #dc2626;">
        <div class="container">
            <h1>🚨 EMERGENCY START HERE</h1>
            <p>Critical information for infrastructure recovery</p>
        </div>
    </header>

    <div class="container">
        <div class="emergency-banner">
            <h2>⚡ If you're reading this, something has gone wrong</h2>
            <p>Don't panic. This guide will help you understand and fix the situation.</p>
        </div>

        <div class="section">
            <h2>📍 STEP 1: Access Password Manager</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <td>{{ emergency.password_manager_type }}</td>
                </tr>
                <tr>
                    <th>URL</th>
                    <td><a href="{{ emergency.password_manager_url }}" target="_blank">{{ emergency.password_manager_url }} ↗</a></td>
                </tr>
                <tr>
                    <th>Emergency Access</th>
                    <td>{{ emergency.password_manager_access }}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>🚨 Critical Services (Must Keep Running)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Service</th>
                        <th>Server</th>
                        <th>Access</th>
                    </tr>
                </thead>
                <tbody>
                    {% for service in emergency.critical_services %}
                    <tr>
                        <td><strong>{{ service.name }}</strong></td>
                        <td>{{ service.server }}</td>
                        <td>{% if service.url %}<a href="{{ service.url }}" target="_blank">Open ↗</a>{% else %}N/A{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📞 Emergency Contacts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Role</th>
                        <th>Contact</th>
                    </tr>
                </thead>
                <tbody>
                    {% for contact in emergency.emergency_contacts %}
                    <tr>
                        <td><strong>{{ contact.name }}</strong></td>
                        <td>{{ contact.role }}</td>
                        <td>
                            {% if contact.phone %}📱 {{ contact.phone }}<br>{% endif %}
                            {% if contact.email %}✉️ {{ contact.email }}{% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>⏰ Immediate Actions (First 5 Minutes)</h2>
            <ol>
                {% for action in emergency.immediate_actions %}
                <li>{{ action }}</li>
                {% endfor %}
            </ol>
        </div>

        <div class="procedure">
            <h3>{{ emergency.disaster_recovery.title }}</h3>
            <p>{{ emergency.disaster_recovery.description }}</p>
            <ol>
                {% for step in emergency.disaster_recovery.steps %}
                <li>{{ step }}</li>
                {% endfor %}
            </ol>
        </div>

        <div class="section">
            <h2>💾 Backup Locations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Location</th>
                        <th>Path</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody>
                    {% for backup in emergency.backup_locations %}
                    <tr>
                        <td><strong>{{ backup.name }}</strong></td>
                        <td><code>{{ backup.path }}</code></td>
                        <td>{{ backup.type }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📅 Timeline of Actions</h2>

            <h3>Within 24 Hours:</h3>
            <ul>
                {% for action in emergency.within_24_hours %}
                <li>{{ action }}</li>
                {% endfor %}
            </ul>

            <h3>Within 1 Week:</h3>
            <ul>
                {% for action in emergency.within_week %}
                <li>{{ action }}</li>
                {% endfor %}
            </ul>

            <h3>Ongoing Maintenance:</h3>
            <ul>
                {% for action in emergency.ongoing_maintenance %}
                <li>{{ action }}</li>
                {% endfor %}
            </ul>
        </div>

        <div class="warning">
            <h3>⚠️ What Can Be Shut Down If Needed</h3>
            <p>These services are nice-to-have but not critical:</p>
            <ul>
                {% for service in emergency.can_shutdown_if_needed %}
                <li>{{ service }}</li>
                {% endfor %}
            </ul>
        </div>

        <footer>
            <p><a href="index.html">← Back to Home</a> | <a href="procedures.html">View All Procedures</a></p>
        </footer>
    </div>
</body>
</html>'''

    def _default_network_template(self) -> str:
        """Default network template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🌐 Network Documentation</h1>
            <p>{{ network.summary }}</p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">← Back to Home</a></li>
            </ul>
        </nav>

        {% if mode.value == 'non_technical' and network.plain_english_summary %}
        <div class="info">
            <h3>In Simple Terms:</h3>
            <p>{{ network.plain_english_summary }}</p>
        </div>
        {% endif %}

        {% if network.reverse_proxy_info %}
        <div class="section">
            <h2>Reverse Proxies</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Server</th>
                        <th>Config Path</th>
                    </tr>
                </thead>
                <tbody>
                    {% for proxy in network.reverse_proxy_info %}
                    <tr>
                        <td><strong>{{ proxy.name }}</strong></td>
                        <td>{{ proxy.type }}</td>
                        <td>{{ proxy.server }}</td>
                        <td><code>{{ proxy.config_path }}</code></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <footer>
            <p><a href="index.html">← Back to Home</a></p>
        </footer>
    </div>
</body>
</html>'''

    def _default_procedures_template(self) -> str:
        """Default procedures template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>📋 Procedures</h1>
            <p>Step-by-step guides for common tasks</p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">← Back to Home</a></li>
                <li><a href="EMERGENCY_START_HERE.html">🚨 Emergency Guide</a></li>
            </ul>
        </nav>

        {% for procedure in procedures %}
        <div class="procedure">
            <h3>{{ procedure.title }}</h3>
            <p>{{ procedure.description }}</p>

            {% if procedure.prerequisites %}
            <h4>Prerequisites:</h4>
            <ul>
                {% for prereq in procedure.prerequisites %}
                <li>{{ prereq }}</li>
                {% endfor %}
            </ul>
            {% endif %}

            {% if procedure.warnings %}
            <div class="warning">
                <strong>⚠️ Warnings:</strong>
                <ul>
                    {% for warning in procedure.warnings %}
                    <li>{{ warning }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            <h4>Steps:</h4>
            <ol>
                {% for step in procedure.steps %}
                <li>{{ step }}</li>
                {% endfor %}
            </ol>
        </div>
        {% endfor %}

        <footer>
            <p><a href="index.html">← Back to Home</a></p>
        </footer>
    </div>
</body>
</html>'''

    def _default_glossary_template(self) -> str:
        """Default glossary template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>📖 Glossary</h1>
            <p>Technical terms explained</p>
        </div>
    </header>

    <div class="container">
        <nav>
            <ul>
                <li><a href="index.html">← Back to Home</a></li>
            </ul>
        </nav>

        <div class="section">
            {% for entry in glossary %}
            <div style="margin-bottom: 25px;">
                <h3>{{ entry.term }}</h3>
                <p><strong>Simple:</strong> {{ entry.plain_english }}</p>
                <p><strong>Technical:</strong> {{ entry.definition }}</p>
                {% if entry.analogy %}
                <p><strong>Analogy:</strong> {{ entry.analogy }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <footer>
            <p><a href="index.html">← Back to Home</a></p>
        </footer>
    </div>
</body>
</html>'''

# Homelab Documentation Generator

**"Hit by a Bus" Documentation System for Self-Hosted Infrastructure**

Automatically scans your entire homelab infrastructure and generates comprehensive, always-up-to-date documentation that allows anyone (even non-technical users) to understand, maintain, and recover your self-hosted services.

## Features

### 🔍 Infrastructure Discovery
- **Automatic Server Detection**: Scans Tailscale network for all connected devices
- **Docker Service Detection**: Discovers all Docker containers and compose configurations
- **Network Mapping**: Maps network topology, reverse proxies, and connections
- **Resource Monitoring**: Tracks CPU, RAM, disk usage across all servers

### 📚 Documentation Generation
- **Server Documentation**: Hardware specs, OS info, services, access methods
- **Service Documentation**: Plain-English explanations, access URLs, dependencies
- **Network Documentation**: Topology diagrams, DNS, firewall rules, SSL certs
- **Critical Procedures**: Emergency shutdown, disaster recovery, backup restoration

### 🤖 AI-Powered Explanations
- **Multi-LLM Support**: Claude, GPT, Ollama, Gemini, OpenAI-compatible APIs
- **Plain-English Translations**: Converts technical details into understandable language
- **Privacy Mode**: Use local Ollama for sensitive system details
- **Troubleshooting Guides**: Automatically generated "if this breaks, do this" procedures

### 📊 Visual Diagrams
- **Infrastructure Topology**: Server and connection visualization
- **Service Dependencies**: Understand what depends on what
- **Data Flow**: See how data moves through your infrastructure
- **Color-Coded Criticality**: Critical/Important/Nice-to-Have classification

### 🔄 Living Documentation
- **Scheduled Updates**: Daily/weekly automatic scans
- **Change Detection**: Highlights what's new or different
- **Version History**: Track infrastructure evolution over time
- **NTFY Notifications**: Get alerted when changes are detected

### 👥 Multiple User Modes
- **Technical Mode**: Full technical details for administrators
- **Non-Technical Mode**: "For My Wife" mode with beginner-friendly explanations
- **Emergency Mode**: Critical information first, quick reference guides

### 📄 Multiple Output Formats
- **Interactive Web Site**: Browse documentation with search and filtering
- **Static HTML**: Works completely offline
- **PDF Book**: Comprehensive printable reference
- **Quick Reference Cards**: One-page guides for common tasks
- **Markdown**: Editable source files

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Access to your infrastructure (Tailscale, SSH keys)
- (Optional) API keys for LLM services

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd Homelab-Documentation-Generator
```

2. Configure your environment:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your infrastructure details
```

3. Start the system:
```bash
docker-compose up -d
```

4. Generate initial documentation:
```bash
docker-compose exec homelab-docs python -m src.cli generate
```

5. Access the web interface:
```
http://localhost:8000
```

## Configuration

Edit `config.yaml` to configure:
- Server list and access credentials
- LLM API keys and preferences
- Scan schedules
- Output formats
- Security settings
- Notification preferences

See [Configuration Guide](docs/configuration.md) for details.

## Usage

### Manual Scan
```bash
# Full infrastructure scan
docker-compose exec homelab-docs python -m src.cli scan

# Generate documentation
docker-compose exec homelab-docs python -m src.cli generate

# Export to PDF
docker-compose exec homelab-docs python -m src.cli export --format pdf
```

### Web Interface
Access http://localhost:8000 for:
- Browse current documentation
- Trigger manual scans
- View change history
- Download exports
- Configure settings

### Emergency Access
The "EMERGENCY_START_HERE.html" file is always generated at the root of the output directory with:
- How to access password manager
- Critical service URLs
- Emergency contacts
- Shutdown procedures
- Backup locations

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Scheduled Scanner                     │
│              (Cron/Systemd Timer)                       │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   Scanner Engine      │
         │  ┌─────────────────┐  │
         │  │ Tailscale       │  │
         │  │ Docker API      │  │
         │  │ SSH/Server Info │  │
         │  │ Network Map     │  │
         │  └─────────────────┘  │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   Data Storage        │
         │   (SQLite/JSON)       │
         │   + Change Tracking   │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │  Documentation        │
         │  Generator Engine     │
         │  ┌─────────────────┐  │
         │  │ Multi-LLM       │  │
         │  │ Templates       │  │
         │  │ Diagrams        │  │
         │  └─────────────────┘  │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌─────▼─────┐    ┌────▼────┐
│  HTML  │    │    PDF    │    │  FastAPI│
│  Static│    │  Export   │    │   Web   │
└────────┘    └───────────┘    └─────────┘
```

## Security

- **No Secrets in Documentation**: All sensitive data references password manager
- **Sanitized Configs**: Environment variables and secrets automatically redacted
- **Access Control**: Web interface supports authentication
- **Encrypted Storage**: Optional encryption for generated documentation
- **Exclusion Lists**: Exclude specific services from documentation

## Project Structure

```
Homelab-Documentation-Generator/
├── src/
│   ├── scanners/          # Infrastructure scanning modules
│   ├── generators/        # Documentation generation
│   ├── llm/              # Multi-LLM integration
│   ├── web/              # FastAPI web interface
│   ├── models/           # Data models
│   └── utils/            # Utilities and helpers
├── templates/            # Documentation templates
├── static/              # Web interface assets
├── data/                # Scanned data and database
├── output/              # Generated documentation
├── docker-compose.yml   # Docker deployment
├── Dockerfile          # Container image
└── config.yaml         # Configuration
```

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT License - See LICENSE file

## Acknowledgments

Built for the "I got hit by a bus" scenario - because your family shouldn't have to figure out your infrastructure in a crisis.

---

**Emergency Contact**: If you're reading this and something is wrong, start with `EMERGENCY_START_HERE.html` in the output directory.

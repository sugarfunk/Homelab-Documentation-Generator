# Getting Started with Homelab Documentation Generator

This guide will help you set up and start using the Homelab Documentation Generator.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (if running locally without Docker)
- SSH access to your servers
- (Optional) API keys for LLM services (Claude, OpenAI, etc.)

### 2. Initial Setup

```bash
# Clone the repository (if you haven't already)
cd Homelab-Documentation-Generator

# Copy the example configuration
cp config.example.yaml config.yaml

# Copy the environment variables template
cp .env.example .env

# Edit config.yaml with your infrastructure details
nano config.yaml  # or use your favorite editor

# Edit .env with your API keys (optional)
nano .env
```

### 3. Configure Your Infrastructure

Edit `config.yaml` and add your servers:

```yaml
infrastructure:
  servers:
    - name: my-server
      hostname: my-server.local
      tailscale_ip: 100.x.x.x
      local_ip: 192.168.1.100
      ssh:
        user: youruser
        key_path: ~/.ssh/id_rsa
        port: 22
      role: primary_server
      criticality: critical
```

### 4. Test Your Configuration

```bash
# Validate configuration
docker-compose run --rm homelab-docs python -m src.cli validate

# Show configuration info
docker-compose run --rm homelab-docs python -m src.cli info
```

### 5. Run Your First Scan

```bash
# Scan your infrastructure
docker-compose run --rm homelab-docs python -m src.cli scan
```

This will:
- Connect to each configured server via SSH
- Collect hardware and OS information
- Scan Docker containers and services
- Find and parse docker-compose files
- Save results to `data/` directory

### 6. Generate Documentation

```bash
# Generate documentation (coming soon - placeholder)
docker-compose run --rm homelab-docs python -m src.cli generate
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Run a one-time scan
docker-compose run --rm homelab-docs python -m src.cli scan

# Start the web interface (when implemented)
docker-compose up -d
```

### With Ollama for Privacy Mode

```bash
# Start with local LLM
docker-compose --profile with-ollama up -d

# Pull a model
docker-compose exec ollama ollama pull llama2
```

## Local Development

### Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run CLI
python -m src.cli --help
```

### Running Scans

```bash
# Scan infrastructure
python -m src.cli scan

# Scan and save to file
python -m src.cli scan --output data/scan-results.json

# Generate documentation
python -m src.cli generate
```

## Configuration Details

### Server Configuration

Each server needs:

- **name**: Unique identifier
- **hostname**: DNS name or IP address
- **ssh**: SSH connection details
  - **user**: SSH username
  - **key_path**: Path to SSH private key
  - **port**: SSH port (default: 22)
- **role**: Server role (primary_server, secondary_server, etc.)
- **criticality**: Importance level (critical, important, nice-to-have)

Optional fields:
- **tailscale_ip**: Tailscale VPN IP
- **local_ip**: Local network IP
- **public_ip**: Public IP address

### LLM Configuration

Configure AI-powered documentation:

```yaml
llm:
  default_provider: claude  # claude, openai, ollama, gemini
  privacy_mode: true        # Use local Ollama for sensitive data
  privacy_provider: ollama

  providers:
    claude:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-5-sonnet-20241022

    ollama:
      base_url: http://ollama:11434
      model: llama2
```

### Scanning Configuration

Control what gets scanned:

```yaml
scanning:
  schedule: "0 2 * * *"  # Cron format for scheduled scans
  enabled_scanners:
    - docker           # Scan Docker containers
    - server_info      # Collect server information
    - compose_files    # Find and parse docker-compose files
```

## Common Tasks

### Add a New Server

1. Edit `config.yaml`
2. Add server to `infrastructure.servers` list
3. Test connection: `python -m src.cli scan`

### Exclude a Service

Add to `config.yaml`:

```yaml
security:
  exclude_services:
    - secret-service-name
```

### Change Output Directory

```yaml
documentation:
  output_dir: /path/to/output
```

## Troubleshooting

### SSH Connection Issues

**Problem**: Can't connect to server

**Solution**:
1. Verify SSH key path is correct
2. Check server is reachable: `ping server-hostname`
3. Test SSH manually: `ssh user@hostname`
4. Check firewall rules

### Docker Socket Permission Denied

**Problem**: Can't access Docker on local machine

**Solution**:
Uncomment in `docker-compose.yml`:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Missing Dependencies

**Problem**: Module not found errors

**Solution**:
```bash
pip install -r requirements.txt
```

## Next Steps

1. **Configure LLM Integration**: Add API keys for AI-powered explanations
2. **Set Up Scheduled Scans**: Use cron or systemd timer
3. **Configure Notifications**: Set up NTFY for change alerts
4. **Customize Documentation**: Edit templates in `templates/` directory
5. **Review Output**: Check generated documentation in `output/` directory

## Getting Help

- Check the [Configuration Guide](configuration.md)
- Review [Examples](examples.md)
- Open an issue on GitHub
- Check logs in `data/homelab_docs.log`

## Security Notes

- **Never commit config.yaml or .env** - they contain secrets!
- SSH keys should have proper permissions (600)
- Use environment variables for API keys
- Enable encryption for generated documentation if sharing
- Review sanitization rules in configuration

## What's Working vs. Coming Soon

### ✅ Currently Implemented

- Server scanning (hardware, OS, resources)
- Docker container detection
- Docker Compose file parsing
- Multi-server infrastructure scanning
- Configuration management
- CLI interface
- Error handling and logging
- Security sanitization framework

### 🚧 Coming Soon

- Full documentation generation
- AI-powered explanations (multi-LLM)
- Diagram generation (topology, dependencies)
- Web interface
- PDF export
- "For My Wife" non-technical mode
- Emergency guide generation
- Change tracking
- Scheduled scans
- NTFY notifications

The foundation is complete - we can extend with these features as needed!

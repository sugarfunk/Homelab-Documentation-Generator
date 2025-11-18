"""FastAPI web application for homelab documentation."""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..utils.config import Config, load_config
from ..scanner_orchestrator import ScannerOrchestrator
from ..generators.doc_generator import DocumentationGenerator
from ..generators.diagram_generator import DiagramGenerator
from ..generators.output_formats import OutputFormatOrchestrator
from ..models.infrastructure import InfrastructureSnapshot


# Pydantic models for API
class ScanRequest(BaseModel):
    """Request to start a scan."""
    enable_ai: bool = True
    generate_docs: bool = True


class ScanStatus(BaseModel):
    """Status of a scan operation."""
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    servers_scanned: int = 0
    services_found: int = 0
    errors: list = []


class DocumentationInfo(BaseModel):
    """Information about generated documentation."""
    generated_at: datetime
    total_servers: int
    total_services: int
    total_containers: int
    output_formats: list
    output_paths: dict


# Global state (in production, use Redis or database)
current_scan_status = ScanStatus(status="idle")
latest_snapshot: Optional[InfrastructureSnapshot] = None


def create_app(config_path: str = "config.yaml") -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured FastAPI app
    """
    # Load configuration
    config = load_config(config_path)

    # Create app
    app = FastAPI(
        title="Homelab Documentation Generator",
        description="Automatic homelab infrastructure documentation system",
        version="1.0.0"
    )

    # Setup logging
    logger = logging.getLogger(__name__)

    # Mount static files if they exist
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))
    else:
        templates = None

    # Serve generated HTML documentation
    output_html_dir = Path(config.documentation.output_dir) / "html"
    if output_html_dir.exists():
        app.mount("/docs", StaticFiles(directory=str(output_html_dir), html=True), name="docs")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home page."""
        if templates:
            return templates.TemplateResponse("web_index.html", {
                "request": request,
                "config": config,
                "scan_status": current_scan_status,
            })

        # Fallback simple HTML
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Homelab Documentation Generator</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; }
                .btn { padding: 10px 20px; margin: 10px; background: #2563eb; color: white; text-decoration: none; border-radius: 5px; display: inline-block; }
                .section { background: #f9fafb; padding: 20px; margin: 20px 0; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>🏠 Homelab Documentation Generator</h1>
            <p>Automatic infrastructure documentation system</p>

            <div class="section">
                <h2>Quick Actions</h2>
                <a href="/api/scan" class="btn">Start New Scan</a>
                <a href="/api/generate" class="btn">Generate Documentation</a>
                <a href="/docs" class="btn">View Documentation</a>
                <a href="/api/status" class="btn">Check Status</a>
            </div>

            <div class="section">
                <h2>API Endpoints</h2>
                <ul>
                    <li><strong>GET /api/status</strong> - Get current status</li>
                    <li><strong>POST /api/scan</strong> - Start infrastructure scan</li>
                    <li><strong>POST /api/generate</strong> - Generate documentation</li>
                    <li><strong>GET /api/snapshot</strong> - Get latest snapshot</li>
                    <li><strong>GET /docs</strong> - View generated documentation</li>
                </ul>
            </div>

            <div class="section">
                <h2>Current Status</h2>
                <pre id="status">Loading...</pre>
            </div>

            <script>
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('status').textContent = JSON.stringify(data, null, 2);
                    });
            </script>
        </body>
        </html>
        """)

    @app.get("/api/status")
    async def get_status():
        """Get current system status."""
        return {
            "scan_status": current_scan_status.dict(),
            "latest_snapshot": {
                "timestamp": latest_snapshot.timestamp.isoformat() if latest_snapshot else None,
                "total_servers": latest_snapshot.total_servers if latest_snapshot else 0,
                "total_services": latest_snapshot.total_services if latest_snapshot else 0,
                "total_containers": latest_snapshot.total_containers if latest_snapshot else 0,
            } if latest_snapshot else None,
            "config": {
                "servers": len(config.infrastructure.servers),
                "output_dir": config.documentation.output_dir,
                "formats": config.documentation.formats,
            }
        }

    @app.post("/api/scan")
    async def start_scan(background_tasks: BackgroundTasks, request: ScanRequest):
        """Start an infrastructure scan."""
        global current_scan_status

        if current_scan_status.status == "running":
            raise HTTPException(status_code=409, detail="Scan already running")

        # Update status
        current_scan_status = ScanStatus(
            status="running",
            started_at=datetime.now()
        )

        # Run scan in background
        background_tasks.add_task(
            run_scan_task,
            config,
            request.enable_ai,
            request.generate_docs
        )

        return {"message": "Scan started", "status": current_scan_status.dict()}

    @app.post("/api/generate")
    async def generate_documentation(background_tasks: BackgroundTasks):
        """Generate documentation from latest snapshot."""
        global latest_snapshot

        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="No snapshot available. Run a scan first.")

        background_tasks.add_task(run_generate_task, config, latest_snapshot)

        return {"message": "Documentation generation started"}

    @app.get("/api/snapshot")
    async def get_snapshot():
        """Get latest infrastructure snapshot."""
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="No snapshot available")

        return latest_snapshot.dict()

    @app.get("/api/servers")
    async def get_servers():
        """Get list of servers."""
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="No snapshot available")

        return [server.dict() for server in latest_snapshot.servers]

    @app.get("/api/services")
    async def get_services():
        """Get list of services."""
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="No snapshot available")

        return [service.dict() for service in latest_snapshot.services]

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    return app


async def run_scan_task(config: Config, enable_ai: bool, generate_docs: bool):
    """Background task to run infrastructure scan.

    Args:
        config: Configuration
        enable_ai: Enable AI features
        generate_docs: Generate documentation after scan
    """
    global current_scan_status, latest_snapshot

    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting infrastructure scan...")

        orchestrator = ScannerOrchestrator(config)
        snapshot = await orchestrator.scan_all()

        # Update global state
        latest_snapshot = snapshot

        current_scan_status = ScanStatus(
            status="completed",
            started_at=current_scan_status.started_at,
            completed_at=datetime.now(),
            servers_scanned=snapshot.total_servers,
            services_found=snapshot.total_services,
            errors=snapshot.scan_errors
        )

        logger.info(f"Scan completed: {snapshot.total_servers} servers, {snapshot.total_services} services")

        # Generate documentation if requested
        if generate_docs:
            await run_generate_task(config, snapshot)

    except Exception as e:
        logger.error(f"Scan failed: {e}")

        current_scan_status = ScanStatus(
            status="failed",
            started_at=current_scan_status.started_at,
            completed_at=datetime.now(),
            errors=[str(e)]
        )


async def run_generate_task(config: Config, snapshot: InfrastructureSnapshot):
    """Background task to generate documentation.

    Args:
        config: Configuration
        snapshot: Infrastructure snapshot
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info("Generating documentation...")

        # Generate documentation
        doc_gen = DocumentationGenerator(config)
        bundle = await doc_gen.generate_full_documentation(snapshot, enable_ai=True)

        # Save bundle
        await doc_gen.save_bundle(bundle)

        # Generate diagrams
        diagram_gen = DiagramGenerator()
        diagrams = diagram_gen.generate_all_diagrams(snapshot)
        bundle.diagrams = diagrams

        # Generate output formats
        output_orchestrator = OutputFormatOrchestrator(
            output_base_dir=Path(config.documentation.output_dir)
        )

        await output_orchestrator.generate_all(bundle, config.documentation.formats)

        logger.info("Documentation generation completed")

    except Exception as e:
        logger.error(f"Documentation generation failed: {e}")


# Entry point for running with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

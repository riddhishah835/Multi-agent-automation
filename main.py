"""
Main Application Entry Point
Wires together all components (P1, P2, P3, P4) and runs the server.
"""

import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging before importing anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# IMPORTS
# ============================================================================

import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import FastAPI app from gateway
from src.api.gateway import app, config_loader, observability, state_manager

# ============================================================================
# VERSION & METADATA
# ============================================================================

__version__ = "1.0.0"
__author__ = "Agentic OS Team"
__description__ = "Multi-tenant orchestration platform for AI agents"


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================

def setup_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "configs",
        "checkpoints",
        "cache",
        "data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def setup_logging():
    """Configure comprehensive logging"""
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create file handler for detailed logs
    file_handler = logging.FileHandler(logs_dir / "app.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)
    logger.info("Logging configured")


def verify_dependencies():
    """Verify that critical dependencies are available"""
    critical_modules = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "yaml",
        "langchain"
    ]
    
    missing = []
    for module in critical_modules:
        try:
            __import__(module)
            logger.info(f"✓ {module} available")
        except ImportError:
            logger.error(f"✗ {module} NOT available")
            missing.append(module)
    
    if missing:
        logger.error(f"Missing critical dependencies: {missing}")
        logger.error("Run: pip install -r requirements.txt")
        return False
    
    logger.info("All critical dependencies verified")
    return True


def print_startup_banner():
    """Print startup banner with useful information"""
    banner = f"""
    
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              🤖 AGENTIC OS - v{__version__}                      ║
    ║              Multi-Tenant AI Orchestration Platform          ║
    ║                                                               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║                                                               ║
    ║  API Documentation:                                           ║
    ║    Swagger UI: http://localhost:8000/docs                    ║
    ║    ReDoc:      http://localhost:8000/redoc                   ║
    ║    OpenAPI:    http://localhost:8000/openapi.json            ║
    ║                                                               ║
    ║  Key Endpoints:                                               ║
    ║    POST   /submit           - Submit new task                ║
    ║    GET    /status/:run_id   - Check task status              ║
    ║    POST   /approve/:run_id  - Approve pending task           ║
    ║    GET    /health           - Health check                   ║
    ║                                                               ║
    ║  Logs:                                                        ║
    ║    Application:  logs/app.log                                ║
    ║    Traces:       logs/traces.jsonl                           ║
    ║    Metrics:      logs/metrics.json                           ║
    ║                                                               ║
    ║  Configuration:                                               ║
    ║    Tenant configs: configs/tenant_*.yaml                     ║
    ║    State checkpoints: checkpoints/                           ║
    ║                                                               ║
    ║  Default Tenant: acme                                         ║
    ║  Auth Format: Bearer tenant_acme_v1                          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    
    """
    print(banner)


def print_environment_info():
    """Print environment and configuration information"""
    env_info = f"""
    
    ═══════════════════════════════════════════════════════════════
    ENVIRONMENT INFORMATION
    ═══════════════════════════════════════════════════════════════
    
    Environment:         {os.getenv('ENVIRONMENT', 'development')}
    Debug Mode:          {os.getenv('DEBUG', 'False')}
    
    API Configuration:
      Host:              {os.getenv('API_HOST', '0.0.0.0')}
      Port:              {os.getenv('API_PORT', '8000')}
      Workers:           {os.getenv('API_WORKERS', '4')}
      Reload:            {os.getenv('API_RELOAD', 'True')}
    
    Redis Configuration:
      Host:              {os.getenv('REDIS_HOST', 'localhost')}
      Port:              {os.getenv('REDIS_PORT', '6379')}
      DB:                {os.getenv('REDIS_DB', '0')}
    
    Database Configuration:
      Type:              {os.getenv('DB_TYPE', 'sqlite')}
      URL:               {os.getenv('DB_URL', 'sqlite:///agentic_os.db')}
    
    LLM Configuration:
      Provider:          {os.getenv('LLM_PROVIDER', 'openai')}
      Model:             {os.getenv('LLM_MODEL', 'gpt-4')}
    
    ═══════════════════════════════════════════════════════════════
    
    """
    print(env_info)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main application entry point"""
    
    logger.info("=" * 70)
    logger.info(f"Starting Agentic OS v{__version__}")
    logger.info("=" * 70)
    
    # Step 1: Setup infrastructure
    logger.info("Step 1: Setting up directories...")
    setup_directories()
    
    # Step 2: Verify dependencies
    logger.info("Step 2: Verifying dependencies...")
    if not verify_dependencies():
        logger.error("Dependency verification failed. Exiting.")
        return False
    
    # Step 3: Log environment
    logger.info("Step 3: Logging environment configuration...")
    print_environment_info()
    
    # Step 4: Print startup banner
    logger.info("Step 4: Printing startup information...")
    print_startup_banner()
    
    # Step 5: Initialize services
    logger.info("Step 5: Initializing services...")
    try:
        config_loader.load_all_configs()
        logger.info("✓ Config loader initialized")
        
        observability.initialize()
        logger.info("✓ Observability tracker initialized")
        
        state_manager.initialize()
        logger.info("✓ State manager initialized")
    
    except Exception as e:
        logger.error(f"Service initialization failed: {str(e)}")
        return False
    
    # Step 6: Start FastAPI server
    logger.info("Step 6: Starting FastAPI server...")
    logger.info("-" * 70)
    
    try:
        # Get configuration from environment
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        workers = int(os.getenv("API_WORKERS", "4"))
        reload = os.getenv("API_RELOAD", "True").lower() == "true"
        
        # Run with uvicorn
        uvicorn.run(
            "src.api.gateway:app",
            host=host,
            port=port,
            workers=workers if not reload else 1,  # Single worker in reload mode
            reload=reload,
            log_level="info",
            access_log=True
        )
        
        logger.info("FastAPI server stopped gracefully")
        return True
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return True
    
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}", exc_info=True)
        return False


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
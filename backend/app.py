import os
import sys
from pathlib import Path

# Add backend directory and parent directory to sys.path
backend_dir = Path(__file__).resolve().parent
parent_dir = backend_dir.parent
for path_dir in [str(backend_dir), str(parent_dir)]:
    if path_dir not in sys.path:
        sys.path.insert(0, path_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

try:
    from dotenv import load_dotenv
    # Load .env from backend_dir or parent_dir
    if (backend_dir / ".env").exists():
        load_dotenv(backend_dir / ".env")
    elif (parent_dir / ".env").exists():
        load_dotenv(parent_dir / ".env")
    else:
        load_dotenv()
    print("Environment variables loaded successfully.")
except ImportError:
    print("python-dotenv not installed. Using default configuration.")

# Port configuration - Support Cloud Run PORT env var with 8080 default
BACKEND_PORT = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8080")))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3001"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# CORS Configuration - Environment-based security
# For production: Set ALLOWED_ORIGINS env var with comma-separated origins
# For development: Uses localhost and ngrok patterns
CUSTOM_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []

# Development origins (only used if ALLOWED_ORIGINS not set)
DEV_ORIGINS = [
    f"http://localhost:{FRONTEND_PORT}",
    f"http://127.0.0.1:{FRONTEND_PORT}",
    "http://localhost:3001",
    "http://localhost:3000",
]

# Choose appropriate CORS configuration
if CUSTOM_ORIGINS and CUSTOM_ORIGINS[0]:  # Production: use explicit origins
    ALLOWED_ORIGINS = CUSTOM_ORIGINS
    USE_WILDCARD = False
elif DEBUG:  # Development: use wildcard for ngrok/Chrome extension
    ALLOWED_ORIGINS = DEV_ORIGINS
    USE_WILDCARD = True
else:  # Production without explicit origins: secure default
    ALLOWED_ORIGINS = DEV_ORIGINS
    USE_WILDCARD = False

print(f"Phishy Platform Configuration:")
print(f"   Backend Port: {BACKEND_PORT}")
print(f"   Frontend Port: {FRONTEND_PORT}")
print(f"   Debug Mode: {DEBUG}")
print(f"   CORS Mode: {'Wildcard (Development)' if USE_WILDCARD else 'Restricted (Production)'}")
if not USE_WILDCARD:
    print(f"   Allowed Origins: {ALLOWED_ORIGINS}")

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "phishy_app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Phishy - Multi-Signal Email Security Analysis Platform",
    version="2.1.0",
    description="Advanced phishing simulation and training platform using multi-signal analysis and explainable AI.",
    contact={
        "name": "Phishy Dev Team",
        "email": "admin@phishy-security.com"
    },
    docs_url="/docs" if DEBUG else None,  # Disable API docs in production
    redoc_url="/redoc" if DEBUG else None,
)

# CORS Middleware - Secure configuration
if USE_WILDCARD:
    # Development mode: Allow all origins for ngrok/Chrome extension
    logger.warning("⚠️  WILDCARD CORS ENABLED - Development mode only!")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
else:
    # Production mode: Restricted origins
    logger.info("✓ Restricted CORS enabled - Production mode")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

routes_loaded = []
routes_failed = []

def load_route_module(module_name: str, prefix: str, tags: list):
    """Helper function to load route modules with error handling"""
    import importlib
    try:
        try:
            module = importlib.import_module(f"routes.{module_name}")
        except ImportError:
            module = importlib.import_module(f"backend.routes.{module_name}")
        
        if hasattr(module, 'router'):
            app.include_router(module.router, prefix=prefix, tags=tags)
            routes_loaded.append(module_name)
            logger.info(f"Module {module_name} loaded successfully")
        else:
            raise ImportError(f"Module {module_name} has no 'router' attribute")
            
    except ImportError as e:
        routes_failed.append(f"{module_name}: Import error - {str(e)}")
        logger.warning(f"Failed to load {module_name}: {e}")
    except Exception as e:
        routes_failed.append(f"{module_name}: {str(e)}")
        logger.error(f"Unexpected error loading {module_name}: {e}")

load_route_module("auth", "/auth", ["🔐 Authentication & Users"])
load_route_module("click_tracker", "/track", ["📊 Click Tracking"])
load_route_module("phishing", "/phishing", ["🎯 Phishing Simulation"])
load_route_module("llm_generator", "/llm", ["🧠 LLM Email Generation"])
load_route_module("analytics", "/analytics", ["📊 Advanced Analytics"])
load_route_module("classifier_endpoint", "/ai/classifier", ["🤖 Intent Classifier"])
load_route_module("smart_query_handler", "/smart", ["🔍 Smart Query Handler"])
load_route_module("phishing_detector", "/detector", ["🛡️ AI Phishing Detection"])
load_route_module("comprehensive_analysis", "/comprehensive", ["🛡️ Comprehensive Security Analysis"])
load_route_module("email_tracking", "/email-track", ["📧 Email Tracking"])
load_route_module("email_flagging", "/email-flagging", ["🚩 Flagged Emails"])
load_route_module("smtp_sender", "/smtp", ["📧 SMTP Email Sender"])

def setup_directories():
    """Create necessary directories"""
    directories = ["data", "training", "logs"]
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_name}")

setup_directories()

def setup_static_files():
    """Setup static file serving"""
    try:
        training_dir = Path("training")
        if training_dir.exists() and any(training_dir.iterdir()):
            app.mount("/training", StaticFiles(directory="training"), name="training")
            logger.info("Training materials mounted at /training")
        else:
            logger.info("Training directory empty, creating default content...")
            training_dir.mkdir(exist_ok=True)
            
            # Create default training page with UPDATED URLs
            default_page = training_dir / "phishing-awareness.html"
            if not default_page.exists():
                default_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phishing Training - Security Awareness</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6;
        }}
        .alert {{ 
            background: #fee; border: 2px solid #fcc; padding: 20px; 
            border-radius: 8px; margin: 20px 0; 
        }}
        .success {{ 
            background: #efe; border: 2px solid #cfc; padding: 20px; 
            border-radius: 8px; margin: 20px 0; 
        }}
        .btn {{ 
            background: #007bff; color: white; padding: 12px 24px; 
            text-decoration: none; border-radius: 6px; display: inline-block;
            transition: background 0.3s;
        }}
        .btn:hover {{ background: #0056b3; }}
        .emoji {{ font-size: 2em; }}
    </style>
</head>
<body>
    <div style="text-align: center;">
        <div class="emoji">🎣</div>
        <h1>You've Been Caught!</h1>
    </div>
    
    <div class="alert">
        <h2>🚨 This was a phishing simulation</h2>
        <p>You clicked on a simulated phishing email. While this was just a training exercise, 
        it demonstrates how easy it can be to fall for phishing attacks.</p>
    </div>
    
    <div class="success">
        <h3>🛡️ How to stay safe:</h3>
        <ul>
            <li><strong>Verify before you click:</strong> Hover over links to see the real destination</li>
            <li><strong>Check the sender:</strong> Look for suspicious email addresses or domains</li>
            <li><strong>Be skeptical of urgency:</strong> Phishers create fake urgency to bypass your judgment</li>
            <li><strong>When in doubt, reach out:</strong> Contact IT or the supposed sender directly</li>
            <li><strong>Report suspicious emails:</strong> Forward them to your security team</li>
        </ul>
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="http://localhost:{FRONTEND_PORT}" class="btn">🏠 Return to Platform</a>
        <a href="http://localhost:{BACKEND_PORT}/docs" class="btn" style="margin-left: 10px;">📚 View API Docs</a>
    </div>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 30px; font-size: 0.9em; color: #666;">
        <p><strong>Training Note:</strong> This simulation helps improve your organization's security awareness. 
        Your interaction has been logged for training analytics to help identify areas where additional 
        security education may be beneficial.</p>
        <p><strong>Platform Info:</strong> Running on ports {BACKEND_PORT} (backend) and {FRONTEND_PORT} (frontend) 
        to avoid conflicts with Splunk (port 8000).</p>
    </div>
</body>
</html>"""
                default_page.write_text(default_content)
                logger.info("Created default training page")
            
            app.mount("/training", StaticFiles(directory="training"), name="training")
            logger.info("Training materials mounted with default content")
            
    except Exception as e:
        logger.warning(f"Failed to mount /training: {e}")

setup_static_files()

def initialize_data_files():
    """Initialize CSV files with proper headers"""
    csv_file = Path("data/click_logs.csv")
    if not csv_file.exists():
        csv_file.parent.mkdir(exist_ok=True)
        with open(csv_file, 'w', newline='') as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(["timestamp", "user_email", "action_id", "ip_address", "user_agent", "referer"])
        logger.info("Created click_logs.csv with headers")

initialize_data_files()

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error", 
            "error": str(exc),
            "type": type(exc).__name__
        }
    )

@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check"""
    data_dir = Path("data")
    csv_file = data_dir / "click_logs.csv"

    fs_status = {
        "data_directory_exists": data_dir.exists(),
        "csv_file_exists": csv_file.exists(),
        "csv_file_size": csv_file.stat().st_size if csv_file.exists() else 0
    }

    data_status = {"csv_readable": False, "record_count": 0}
    if csv_file.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_file)
            data_status["csv_readable"] = True
            data_status["record_count"] = len(df)
        except Exception as e:
            data_status["error"] = str(e)
    
    return {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": f"{datetime.utcnow().isoformat()}Z",
        "port_configuration": {
            "backend_port": BACKEND_PORT,
            "frontend_port": FRONTEND_PORT,
            "note": "Updated to avoid Splunk conflicts (port 8000)"
        },
        "routes_loaded": routes_loaded,
        "routes_failed": routes_failed,
        "file_system": fs_status,
        "data_integrity": data_status,
        "available_endpoints": len(app.routes)
    }

@app.get("/", tags=["System"])
def root_info():
    """Root endpoint with platform information"""
    return {
        "message": "🎣 Welcome to Phishy - Advanced Cybersecurity Training Platform",
        "version": "2.1.0",
        "status": "running",
        "description": "AI-powered phishing simulation and security awareness training platform",
        "port_configuration": {
            "backend_port": BACKEND_PORT,
            "frontend_port": FRONTEND_PORT,
            "note": "Configured to avoid Splunk conflicts"
        },
        "features": {
            "ai_email_generation": "mistral:7b" in str(routes_loaded),
            "advanced_analytics": "analytics" in routes_loaded,
            "admin_assistant": "admin_assistant" in routes_loaded,
            "forecasting": "forecast" in routes_loaded,
            "historical_queries": "historical_query" in routes_loaded,
            "click_tracking": "click_tracker" in routes_loaded
        },
        "loaded_modules": routes_loaded,
        "failed_modules": routes_failed,
        "endpoints": {
            "api_documentation": f"http://localhost:{BACKEND_PORT}/docs",
            "alternative_docs": f"http://localhost:{BACKEND_PORT}/redoc",
            "health_check": f"http://localhost:{BACKEND_PORT}/health",
            "click_tracking": f"http://localhost:{BACKEND_PORT}/track/click",
            "training_page": f"http://localhost:{BACKEND_PORT}/training/phishing-awareness.html",
            "frontend_interface": f"http://localhost:{FRONTEND_PORT}",
            "generate_ai_email": f"http://localhost:{BACKEND_PORT}/llm/generate-email",
            "analytics": f"http://localhost:{BACKEND_PORT}/analytics/analyze",
            "admin_query": f"http://localhost:{BACKEND_PORT}/admin/query",
            "intelligent_query": f"http://localhost:{BACKEND_PORT}/ai/intelligent-query"
        },
        "quick_start": {
            "1": f"Visit http://localhost:{FRONTEND_PORT} for the web interface",
            "2": f"Visit http://localhost:{BACKEND_PORT}/docs for interactive API documentation",
            "3": "Use /llm/generate-email to create phishing simulations",
            "4": "Track clicks with /track/click endpoint",
            "5": "Analyze data with /analytics/analyze",
            "6": "Query historical data with /query/historical"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Phishy Platform starting up...")
    try:
        from database import init_db
        init_db()
        logger.info("SQLite Database ready")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}")
    logger.info(f"Backend server starting on: http://{HOST}:{BACKEND_PORT}")
    logger.info(f"Frontend should run on: http://localhost:{FRONTEND_PORT}")
    logger.info(f"API Documentation: http://localhost:{BACKEND_PORT}/docs")
    logger.info(f"Training Page: http://localhost:{BACKEND_PORT}/training/phishing-awareness.html")
    logger.info(f"Note: Ports configured to avoid Splunk conflicts (avoiding port 8000)")
    logger.info(f"Loaded modules: {', '.join(routes_loaded) if routes_loaded else 'None'}")
    
    if routes_failed:
        logger.warning(f"Failed modules: {', '.join(routes_failed)}")
        logger.info("Some features may be running in fallback mode")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Phishy Platform shutting down...")
    logger.info("Thank you for using Phishy!")

if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting Phishy Platform")
    print(f"Backend: http://{HOST}:{BACKEND_PORT}")
    print(f"Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"API Docs: http://localhost:{BACKEND_PORT}/docs")
    print(f"Note: Using port {BACKEND_PORT} to avoid Splunk conflict on port 8000")
    print("=" * 60)
    
    uvicorn.run(
        "app:app",
        host=HOST,
        port=BACKEND_PORT,
        reload=DEBUG,
        log_level="info"
    )
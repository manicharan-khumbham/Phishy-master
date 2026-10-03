"""
Email Flagging Plugin System
Optimized for ngrok tunneling and email client integration
"""
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
import logging
import json
import csv
import os
import uuid
import asyncio
from pathlib import Path
import qrcode
import base64
from io import BytesIO

router = APIRouter()
logger = logging.getLogger(__name__)

# Setup data paths
DATA_DIR = Path("data")
FLAGGED_EMAILS_FILE = DATA_DIR / "flagged_emails.csv"
PLUGIN_CONFIGS_FILE = DATA_DIR / "plugin_configs.json"
TUNNEL_STATUS_FILE = DATA_DIR / "tunnel_status.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.plugin_connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, plugin_type: str = None):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if plugin_type:
            if plugin_type not in self.plugin_connections:
                self.plugin_connections[plugin_type] = {}
            self.plugin_connections[plugin_type][client_id] = websocket
        
        logger.info(f"WebSocket connected: {client_id} ({plugin_type or 'unknown'})")
    
    def disconnect(self, client_id: str, plugin_type: str = None):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if plugin_type and plugin_type in self.plugin_connections:
            if client_id in self.plugin_connections[plugin_type]:
                del self.plugin_connections[plugin_type][client_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_to_plugins(self, message: dict, plugin_type: str = None):
        if plugin_type and plugin_type in self.plugin_connections:
            connections = self.plugin_connections[plugin_type]
        else:
            connections = self.active_connections
        
        disconnected = []
        for client_id, connection in connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id, plugin_type)

manager = ConnectionManager()

# Pydantic models
class EmailFlagRequest(BaseModel):
    """Email flagging request from plugin"""
    email_id: str = Field(..., description="Unique email identifier")
    sender_email: str = Field(..., description="Email sender address")
    subject: str = Field(..., description="Email subject line")
    body: Optional[str] = Field(None, description="Email body content")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Email headers")
    flag_category: Literal["phishing", "spam", "malware", "suspicious", "other"] = Field(..., description="Flag category")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0-1)")
    user_email: str = Field(..., description="User who flagged the email")
    client_info: Optional[Dict[str, str]] = Field(default_factory=dict, description="Client information")
    plugin_version: Optional[str] = Field(None, description="Plugin version")
    additional_context: Optional[str] = Field(None, description="Additional context or notes")

class PluginConfig(BaseModel):
    """Plugin configuration model"""
    plugin_id: str = Field(..., description="Unique plugin identifier")
    plugin_type: Literal["outlook", "gmail", "thunderbird"] = Field(..., description="Email client type")
    tunnel_url: str = Field(..., description="Current ngrok tunnel URL")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    user_email: str = Field(..., description="User's email address")
    organization: Optional[str] = Field(None, description="Organization name")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plugin-specific settings")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True, description="Plugin active status")

class TunnelStatus(BaseModel):
    """Ngrok tunnel status model"""
    tunnel_url: str = Field(..., description="Current tunnel URL")
    public_url: str = Field(..., description="Public ngrok URL")
    status: Literal["active", "inactive", "error"] = Field(..., description="Tunnel status")
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    connected_plugins: int = Field(default=0, description="Number of connected plugins")

class EmailAnalysisResult(BaseModel):
    """AI analysis result for flagged email"""
    is_suspicious: bool = Field(..., description="Whether email is suspicious")
    threat_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Threat level")
    threat_types: List[str] = Field(default_factory=list, description="Detected threat types")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    explanation: str = Field(..., description="Human-readable explanation")
    recommendations: List[str] = Field(default_factory=list, description="Security recommendations")

# Initialize CSV file for flagged emails
def initialize_flagged_emails_csv():
    """Initialize CSV file with proper headers"""
    if not FLAGGED_EMAILS_FILE.exists():
        try:
            with open(FLAGGED_EMAILS_FILE, mode="w", newline="", encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "timestamp", "email_id", "sender_email", "subject", "flag_category",
                    "confidence_level", "user_email", "plugin_type", "plugin_version",
                    "threat_level", "ai_confidence", "additional_context", "status"
                ])
            logger.info("📄 Initialized flagged_emails.csv with headers")
        except Exception as e:
            logger.error(f"Failed to initialize flagged emails CSV: {e}")
            raise

initialize_flagged_emails_csv()

# Helper functions
def load_plugin_configs() -> Dict[str, PluginConfig]:
    """Load plugin configurations from file"""
    if not PLUGIN_CONFIGS_FILE.exists():
        return {}
    
    try:
        with open(PLUGIN_CONFIGS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return {
                plugin_id: PluginConfig(**config) 
                for plugin_id, config in data.items()
            }
    except Exception as e:
        logger.error(f"Error loading plugin configs: {e}")
        return {}

def save_plugin_configs(configs: Dict[str, PluginConfig]):
    """Save plugin configurations to file"""
    try:
        data = {
            plugin_id: config.model_dump(mode='json')
            for plugin_id, config in configs.items()
        }
        with open(PLUGIN_CONFIGS_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, default=str)
        logger.info("Plugin configurations saved successfully")
    except Exception as e:
        logger.error(f"Error saving plugin configs: {e}")
        raise

def get_current_tunnel_status() -> Optional[TunnelStatus]:
    """Get current tunnel status"""
    if not TUNNEL_STATUS_FILE.exists():
        return None
    
    try:
        with open(TUNNEL_STATUS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return TunnelStatus(**data)
    except Exception as e:
        logger.error(f"Error loading tunnel status: {e}")
        return None

def save_tunnel_status(status: TunnelStatus):
    """Save tunnel status to file"""
    try:
        with open(TUNNEL_STATUS_FILE, 'w', encoding='utf-8') as file:
            json.dump(status.model_dump(mode='json'), file, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving tunnel status: {e}")

def log_flagged_email(flag_request: EmailFlagRequest, analysis_result: EmailAnalysisResult):
    """Log flagged email to CSV and SQLite DB"""
    try:
        with open(FLAGGED_EMAILS_FILE, mode="a", newline="", encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                flag_request.email_id,
                flag_request.sender_email,
                flag_request.subject,
                flag_request.flag_category,
                flag_request.confidence_level,
                flag_request.user_email,
                flag_request.client_info.get('plugin_type', 'unknown') if flag_request.client_info else 'unknown',
                flag_request.plugin_version or 'unknown',
                analysis_result.threat_level,
                analysis_result.confidence_score,
                flag_request.additional_context or '',
                'pending'
            ])
    except Exception as e:
        logger.error(f"Failed to log flagged email to CSV: {e}")

    try:
        from database import db_add_flagged_email
        db_add_flagged_email(
            flag_request.email_id,
            flag_request.sender_email,
            flag_request.subject,
            flag_request.flag_category,
            flag_request.confidence_level,
            flag_request.user_email,
            analysis_result.threat_level,
            analysis_result.confidence_score,
            flag_request.additional_context
        )
    except Exception as e:
        logger.error(f"Failed to log flagged email to SQLite DB: {e}")

async def analyze_email_with_ai(flag_request: EmailFlagRequest) -> EmailAnalysisResult:
    """Analyze flagged email using AI (placeholder for actual AI integration)"""
    # This is a simplified analysis - in production, integrate with your AI model
    
    # Basic heuristics for demonstration
    threat_indicators = []
    threat_level = "low"
    confidence = 0.5
    
    # Check for common phishing indicators
    subject_lower = flag_request.subject.lower()
    body_lower = (flag_request.body or '').lower()
    
    if any(word in subject_lower for word in ['urgent', 'verify', 'suspended', 'click here']):
        threat_indicators.append("suspicious_subject")
        confidence += 0.2
    
    if any(word in body_lower for word in ['login', 'password', 'account', 'verify']):
        threat_indicators.append("credential_request")
        confidence += 0.2
    
    # Determine threat level based on confidence
    if confidence >= 0.8:
        threat_level = "critical"
    elif confidence >= 0.6:
        threat_level = "high"
    elif confidence >= 0.4:
        threat_level = "medium"
    
    return EmailAnalysisResult(
        is_suspicious=confidence >= 0.3,
        threat_level=threat_level,
        threat_types=threat_indicators,
        confidence_score=min(confidence, 1.0),
        explanation=f"Email flagged as {flag_request.flag_category} with {len(threat_indicators)} threat indicators",
        recommendations=[
            "Do not click any links in this email",
            "Verify sender identity through alternative means",
            "Report to IT security team"
        ] if confidence >= 0.5 else ["Monitor for similar patterns"]
    )

# API Endpoints

@router.post("/flag")
async def flag_email(flag_request: EmailFlagRequest, request: Request):
    """
    Flag an email as suspicious from email client plugin
    """
    try:
        logger.info(f"Email flagged by {flag_request.user_email}: {flag_request.subject}")
        
        # Analyze email with AI
        analysis_result = await analyze_email_with_ai(flag_request)
        
        # Log to CSV
        log_flagged_email(flag_request, analysis_result)
        
        # Broadcast to connected admin dashboards
        await manager.broadcast_to_plugins({
            "type": "email_flagged",
            "data": {
                "flag_request": flag_request.model_dump(mode='json'),
                "analysis": analysis_result.model_dump(mode='json'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }, "admin")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Email flagged successfully",
            "email_id": flag_request.email_id,
            "analysis": analysis_result.model_dump(mode='json'),
            "flagged_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error flagging email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to flag email: {str(e)}")

@router.get("/flags")
async def get_flagged_emails(
    limit: Optional[int] = 100,
    category: Optional[str] = None,
    user_email: Optional[str] = None,
    days: Optional[int] = None
):
    """
    Retrieve flagged emails from SQLite database with optional filtering
    """
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM flagged_emails WHERE 1=1"
        params = []
        
        if category:
            query += " AND flag_category = ?"
            params.append(category)
        if user_email:
            query += " AND user_email = ?"
            params.append(user_email)
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit or 100)
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        
        flagged_emails = [dict(row) for row in rows]
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Retrieved {len(flagged_emails)} flagged emails",
            "total_count": len(flagged_emails),
            "flagged_emails": flagged_emails,
            "data": flagged_emails
        })
        
    except Exception as e:
        logger.error(f"Error retrieving flagged emails from SQLite DB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve flagged emails: {str(e)}")

@router.post("/plugins/register")
async def register_plugin(config: PluginConfig):
    """
    Register a new email client plugin
    """
    try:
        configs = load_plugin_configs()
        
        # Update last_updated timestamp
        config.last_updated = datetime.now(timezone.utc)
        
        configs[config.plugin_id] = config
        save_plugin_configs(configs)
        
        logger.info(f"Plugin registered: {config.plugin_id} ({config.plugin_type})")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Plugin registered successfully",
            "plugin_id": config.plugin_id,
            "setup_url": f"/plugins/setup/{config.plugin_id}"
        })
        
    except Exception as e:
        logger.error(f"Error registering plugin: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register plugin: {str(e)}")

@router.get("/plugins")
async def list_plugins():
    """
    List all registered plugins
    """
    try:
        configs = load_plugin_configs()
        
        # Update connection status
        plugin_list = []
        for plugin_id, config in configs.items():
            plugin_data = config.model_dump(mode='json')
            
            # Check if plugin is currently connected
            plugin_data['is_connected'] = plugin_id in manager.active_connections
            plugin_data['connection_count'] = len(manager.plugin_connections.get(config.plugin_type, {}))
            
            plugin_list.append(plugin_data)
        
        return JSONResponse(content={
            "message": f"Found {len(plugin_list)} registered plugins",
            "plugins": plugin_list,
            "total_connections": len(manager.active_connections)
        })
        
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list plugins: {str(e)}")

@router.get("/plugins/setup/{plugin_id}")
async def get_plugin_setup_info(plugin_id: str):
    """
    Get plugin setup information and generate QR code
    """
    try:
        configs = load_plugin_configs()
        tunnel_status = get_current_tunnel_status()
        
        if plugin_id in configs:
            config = configs[plugin_id]
            plugin_type = config.plugin_type
            tunnel_url = tunnel_status.tunnel_url if tunnel_status else config.tunnel_url
        elif plugin_id.lower() in ["gmail", "outlook", "thunderbird"]:
            plugin_type = plugin_id.lower()
            tunnel_url = tunnel_status.tunnel_url if tunnel_status else "http://localhost:8080"
        else:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        setup_data = {
            "plugin_id": plugin_id,
            "plugin_type": plugin_type,
            "tunnel_url": tunnel_url,
            "api_endpoints": {
                "flag": f"{tunnel_url}/email-flagging/flag",
                "websocket": f"{tunnel_url}/email-flagging/ws/{plugin_id}",
                "health": f"{tunnel_url}/email-flagging/health"
            },
            "setup_instructions": get_setup_instructions(plugin_type)
        }
        
        # Generate QR code for easy setup
        qr_data = json.dumps(setup_data)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Convert QR code to base64
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        setup_data['qr_code'] = f"data:image/png;base64,{qr_base64}"
        
        return JSONResponse(content=setup_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin setup info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setup info: {str(e)}")

def get_setup_instructions(plugin_type: str) -> List[str]:
    """Get setup instructions for specific plugin type"""
    instructions = {
        "outlook": [
            "1. Download the Phishy Outlook plugin from the setup URL",
            "2. Open Outlook and go to File > Options > Add-ins",
            "3. Click 'Go' next to COM Add-ins",
            "4. Click 'Add' and browse to the plugin file",
            "5. Enter the tunnel URL in plugin settings",
            "6. Test connection using the health check"
        ],
        "gmail": [
            "1. Install the Phishy Chrome extension from setup URL",
            "2. Open Gmail in Chrome browser",
            "3. Click the Phishy extension icon",
            "4. Enter the tunnel URL in extension settings",
            "5. Grant necessary permissions",
            "6. Test by flagging a test email"
        ],
        "thunderbird": [
            "1. Download the Phishy Thunderbird extension",
            "2. Open Thunderbird and go to Tools > Add-ons",
            "3. Click the gear icon and select 'Install Add-on from File'",
            "4. Select the downloaded extension file",
            "5. Configure tunnel URL in extension preferences",
            "6. Restart Thunderbird to complete setup"
        ]
    }
    return instructions.get(plugin_type, ["Setup instructions not available"])

@router.get("/tunnel/status")
async def get_tunnel_status():
    """
    Get current ngrok tunnel status
    """
    try:
        tunnel_status = get_current_tunnel_status()
        
        if not tunnel_status:
            return JSONResponse(content={
                "status": "inactive",
                "message": "No tunnel status found",
                "connected_plugins": 0
            })
        
        # Update connected plugins count
        tunnel_status.connected_plugins = len(manager.active_connections)
        tunnel_status.last_checked = datetime.now(timezone.utc)
        
        save_tunnel_status(tunnel_status)
        
        return JSONResponse(content=tunnel_status.model_dump(mode='json'))
        
    except Exception as e:
        logger.error(f"Error getting tunnel status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tunnel status: {str(e)}")

@router.post("/tunnel/update")
async def update_tunnel_url(tunnel_url: str, public_url: str = None):
    """
    Update ngrok tunnel URL when it changes
    """
    try:
        tunnel_status = TunnelStatus(
            tunnel_url=tunnel_url,
            public_url=public_url or tunnel_url,
            status="active",
            connected_plugins=len(manager.active_connections)
        )
        
        save_tunnel_status(tunnel_status)
        
        # Broadcast tunnel update to all connected plugins
        await manager.broadcast_to_plugins({
            "type": "tunnel_updated",
            "data": {
                "new_tunnel_url": tunnel_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
        
        logger.info(f"Tunnel URL updated: {tunnel_url}")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Tunnel URL updated successfully",
            "tunnel_url": tunnel_url,
            "notified_plugins": len(manager.active_connections)
        })
        
    except Exception as e:
        logger.error(f"Error updating tunnel URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update tunnel URL: {str(e)}")

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, plugin_type: str = None):
    """
    WebSocket endpoint for real-time communication with plugins
    """
    await manager.connect(websocket, client_id, plugin_type)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to Phishy AI",
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, client_id)
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, client_id)
            
            elif message.get("type") == "status_update":
                # Handle plugin status updates
                logger.info(f"Status update from {client_id}: {message.get('status')}")
            
    except WebSocketDisconnect:
        manager.disconnect(client_id, plugin_type)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id, plugin_type)

@router.get("/health")
async def health_check():
    """
    Health check endpoint for plugins to verify connectivity
    """
    try:
        tunnel_status = get_current_tunnel_status()
        
        return JSONResponse(content={
            "status": "healthy",
            "message": "Phishy AI Email Flagging System is operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tunnel_active": tunnel_status.status == "active" if tunnel_status else False,
            "connected_plugins": len(manager.active_connections),
            "version": "1.0.0"
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@router.get("/stats")
async def get_flagging_stats():
    """
    Get email flagging statistics
    """
    try:
        if not FLAGGED_EMAILS_FILE.exists():
            return JSONResponse(content={
                "total_flags": 0,
                "categories": {},
                "threat_levels": {},
                "top_flaggers": {},
                "recent_activity": []
            })
        
        stats = {
            "total_flags": 0,
            "categories": {},
            "threat_levels": {},
            "top_flaggers": {},
            "plugin_types": {}
        }
        
        with open(FLAGGED_EMAILS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                stats["total_flags"] += 1
                
                # Count categories
                category = row['flag_category']
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                
                # Count threat levels
                threat_level = row['threat_level']
                stats["threat_levels"][threat_level] = stats["threat_levels"].get(threat_level, 0) + 1
                
                # Count top flaggers
                user = row['user_email']
                stats["top_flaggers"][user] = stats["top_flaggers"].get(user, 0) + 1
                
                # Count plugin types
                plugin_type = row['plugin_type']
                stats["plugin_types"][plugin_type] = stats["plugin_types"].get(plugin_type, 0) + 1
        
        return JSONResponse(content={
            "message": "Email flagging statistics",
            "stats": stats,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting flagging stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
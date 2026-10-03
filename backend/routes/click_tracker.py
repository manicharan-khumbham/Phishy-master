from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from datetime import datetime
import logging
import csv
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
LOG_FILE = DATA_DIR / "click_logs.csv"
TEXT_LOG_FILE = DATA_DIR / "click_logs.txt"

DATA_DIR.mkdir(exist_ok=True)

file_handler = logging.FileHandler(TEXT_LOG_FILE)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

click_logger = logging.getLogger('click_tracker')
click_logger.addHandler(file_handler)
click_logger.setLevel(logging.INFO)

def initialize_csv():
    """Initialize CSV file with proper headers"""
    if not LOG_FILE.exists():
        try:
            with open(LOG_FILE, mode="w", newline="", encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["timestamp", "user_email", "action_id", "ip_address", "user_agent", "referer"])
            logger.info("Initialized click_logs.csv with headers")
        except Exception as e:
            logger.error(f"Failed to initialize CSV file: {e}")
            raise

initialize_csv()

def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client IP, user agent, and referer from request"""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer", "direct")
    }

def log_click_to_csv(timestamp: str, user_email: str, action_id: str, client_info: Dict[str, str]):
    """Log click data to CSV file and SQLite database"""
    try:
        with open(LOG_FILE, mode="a", newline="", encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                timestamp,
                user_email,
                action_id,
                client_info["ip_address"],
                client_info["user_agent"],
                client_info["referer"]
            ])
    except Exception as e:
        logger.error(f"Failed to write to CSV: {e}")
        
    try:
        from database import db_add_click_log
        db_add_click_log(user_email, action_id, client_info["ip_address"], client_info["user_agent"], client_info["referer"])
    except Exception as e:
        logger.error(f"Failed to write click log to SQLite DB: {e}")

@router.get("/click")
def track_click(
    request: Request,
    user_email: str = Query(..., description="User email address"),
    action: str = Query(..., description="Action identifier"),
    redirect_url: Optional[str] = Query("/training/phishing-awareness.html", description="Redirect URL after tracking")
):
    """
    Track user clicks on phishing simulation emails
    
    This endpoint logs the click event and redirects the user to a training page.
    """
    try:
        client_info = get_client_info(request)
        timestamp = datetime.utcnow().isoformat()

        log_entry = f"{timestamp} - {user_email} - {action} - {client_info['ip_address']} - {client_info['user_agent'][:100]}"
        click_logger.info(log_entry)

        log_click_to_csv(timestamp, user_email, action, client_info)

        logger.info(f"Tracked click: {user_email} -> {action}")

        if redirect_url and not redirect_url.startswith('/'):
            # Restrict external redirects to prevent Open Redirect vulnerability
            if not redirect_url.startswith(('http://localhost', 'https://localhost', 'http://127.0.0.1', 'https://127.0.0.1')):
                redirect_url = "/training/phishing-awareness.html"

        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        # Still redirect to training page even if logging fails
        return RedirectResponse(url="/training/phishing-awareness.html", status_code=302)

@router.get("/logs")
def get_click_logs(
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    action_id: Optional[str] = Query(None, description="Filter by action ID"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter by number of days back"),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format")
):
    """
    Retrieve click logs directly from SQLite Database with optional filtering
    """
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT timestamp, user_email, action_id, ip_address, user_agent, referer FROM click_logs WHERE 1=1"
        params = []
        
        if user_email:
            query += " AND user_email LIKE ?"
            params.append(f"%{user_email}%")
        if action_id:
            query += " AND action_id LIKE ?"
            params.append(f"%{action_id}%")
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        records = [dict(row) for row in rows]

        if format == "csv":
            df = pd.DataFrame(records)
            filtered_file = DATA_DIR / "filtered_logs.csv"
            df.to_csv(filtered_file, index=False)
            return FileResponse(
                filtered_file,
                media_type='text/csv',
                filename=f"click_logs_filtered_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            )
        else:
            return JSONResponse(content={
                "message": f"Retrieved {len(records)} log entries from SQLite DB",
                "total_records": len(records),
                "filters_applied": {
                    "user_email": user_email,
                    "action_id": action_id,
                    "days_back": days,
                    "limit": limit
                },
                "data": records
            })

    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@router.get("/logs/csv")
def download_csv():
    """
    Download complete click logs as CSV file
    
    Returns the complete click tracking CSV file for download.
    """
    try:
        if not LOG_FILE.exists():
            raise HTTPException(status_code=404, detail="No log file found")

        return FileResponse(
            LOG_FILE,
            media_type='text/csv',
            filename=f"click_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    except Exception as e:
        logger.error(f"Error downloading CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download CSV: {str(e)}")

@router.get("/stats")
def get_click_stats():
    """
    Get basic statistics about click tracking data
    
    Returns summary statistics about the tracked clicks.
    """
    try:
        if not LOG_FILE.exists():
            return JSONResponse(content={
                "message": "No log data available",
                "stats": {"total_clicks": 0, "unique_users": 0, "unique_actions": 0}
            })

        df = pd.read_csv(LOG_FILE)

        if df.empty:
            return JSONResponse(content={
                "message": "No log data available",
                "stats": {"total_clicks": 0, "unique_users": 0, "unique_actions": 0}
            })

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        now = datetime.utcnow()

        stats = {
            "total_clicks": len(df),
            "unique_users": df['user_email'].nunique(),
            "unique_actions": df['action_id'].nunique(),
            "unique_ips": df['ip_address'].nunique(),
            "date_range": {
                "first_click": df['timestamp'].min().isoformat(),
                "last_click": df['timestamp'].max().isoformat(),
                "span_days": (df['timestamp'].max() - df['timestamp'].min()).days
            },
            "recent_activity": {
                "last_24h": len(df[df['timestamp'] > (now - pd.Timedelta(hours=24))]),
                "last_7d": len(df[df['timestamp'] > (now - pd.Timedelta(days=7))]),
                "last_30d": len(df[df['timestamp'] > (now - pd.Timedelta(days=30))])
            },
            "top_users": df['user_email'].value_counts().head(10).to_dict(),
            "top_actions": df['action_id'].value_counts().head(10).to_dict(),
            "hourly_distribution": df.groupby(df['timestamp'].dt.hour).size().to_dict()
        }

        return JSONResponse(content={
            "message": "Click tracking statistics",
            "generated_at": now.isoformat(),
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error generating stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate statistics: {str(e)}")

@router.delete("/logs")
def clear_logs(confirm: bool = Query(False, description="Confirmation required to clear logs")):
    """
    Clear all click tracking logs
    
    ⚠️ WARNING: This will permanently delete all click tracking data!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Add ?confirm=true to clear all logs."
        )

    try:
        if LOG_FILE.exists():
            backup_file = DATA_DIR / f"click_logs_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            LOG_FILE.rename(backup_file)
            logger.info(f"Backed up logs to {backup_file}")

        initialize_csv()

        if TEXT_LOG_FILE.exists():
            TEXT_LOG_FILE.write_text("")

        logger.info("All click logs cleared")

        return JSONResponse(content={
            "message": "All logs cleared successfully",
            "backup_created": str(backup_file) if 'backup_file' in locals() else None,
            "cleared_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")

@router.get("/health")
def get_tracker_health():
    """
    Health check for click tracking system
    """
    try:
        health_status = {
            "status": "healthy",
            "data_directory_exists": DATA_DIR.exists(),
            "csv_file_exists": LOG_FILE.exists(),
            "csv_file_writable": os.access(LOG_FILE.parent, os.W_OK),
            "csv_file_size": LOG_FILE.stat().st_size if LOG_FILE.exists() else 0,
        }

        if LOG_FILE.exists():
            try:
                df = pd.read_csv(LOG_FILE)
                health_status["csv_readable"] = True
                health_status["record_count"] = len(df)
            except Exception as e:
                health_status["csv_readable"] = False
                health_status["csv_error"] = str(e)
                health_status["status"] = "unhealthy"
        else:
            health_status["csv_readable"] = False
            health_status["record_count"] = 0

        return JSONResponse(content=health_status)

    except Exception as e:
        return JSONResponse(content={
            "status": "unhealthy",
            "error": str(e)
        }, status_code=500)
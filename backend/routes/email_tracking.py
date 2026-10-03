from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import csv
import os
import logging
import pandas as pd
import base64
from uuid import uuid4
import json

router = APIRouter()
logger = logging.getLogger(__name__)

class EmailOpenData(BaseModel):
    user_email: str
    action_id: str
    timestamp: str
    ip_address: str
    user_agent: Optional[str] = None
    campaign_id: Optional[str] = None

class TrackingStats(BaseModel):
    total_opens: int
    unique_users: int
    total_sent: int
    open_rate: float
    users_opened: List[Dict[str, Any]]
    hourly_distribution: Dict[str, int]
    recent_opens: List[Dict[str, Any]]

def get_email_opens_file():
    """Get the path to the email opens CSV file"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "email_opens.csv")

def log_email_open(user_email: str, action_id: str, ip_address: str, user_agent: str = None, campaign_id: str = None):
    """Log email open to CSV file and SQLite DB"""
    try:
        opens_file = get_email_opens_file()
        if not os.path.exists(opens_file):
            with open(opens_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "user_email", "action_id", "ip_address", "user_agent", "campaign_id"])
        
        with open(opens_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.utcnow().isoformat(),
                user_email,
                action_id,
                ip_address,
                user_agent or "Unknown",
                campaign_id or ""
            ])
    except Exception as e:
        logger.error(f"Failed to log email open to CSV: {e}")

    try:
        from database import db_add_email_open
        db_add_email_open(user_email, action_id, ip_address, user_agent, campaign_id)
        logger.info(f"Logged email open to SQLite DB: {user_email} - {action_id}")
    except Exception as e:
        logger.error(f"Failed to log email open to SQLite DB: {e}")

def load_email_opens_data() -> pd.DataFrame:
    """Load email opens data directly from SQLite Database"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT timestamp, user_email, action_id, ip_address, user_agent, campaign_id FROM email_opens", conn)
        conn.close()
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        logger.error(f"Error reading email opens from SQLite DB: {e}")
        opens_file = get_email_opens_file()
        if not os.path.exists(opens_file):
            return pd.DataFrame(columns=["timestamp", "user_email", "action_id", "ip_address", "user_agent", "campaign_id"])
        return pd.read_csv(opens_file)

def generate_pixel_image():
    """Generate a 1x1 transparent PNG pixel"""
    # 1x1 transparent PNG in base64
    pixel_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGA'
        'hkFjQgAAAABJRU5ErkJggg=='
    )
    return pixel_data

@router.get("/pixel/{tracking_id}")
async def serve_tracking_pixel(
    tracking_id: str, 
    request: Request,
    user_email: str = Query(None),
    action: str = Query(None),
    campaign: str = Query(None)
):
    """
    Serve 1x1 transparent tracking pixel and log email open
    
    URL format: /track/pixel/{tracking_id}?user_email=user@example.com&action=action_id&campaign=campaign_id
    """
    try:
        # Get client IP address
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            client_ip = request.headers["x-real-ip"]
        
        # Get user agent
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Use tracking_id as action_id if action not provided
        action_id = action or tracking_id
        
        # Log the email open if we have user email
        if user_email:
            log_email_open(user_email, action_id, client_ip, user_agent, campaign)
        else:
            logger.warning(f"Tracking pixel accessed without user_email: {tracking_id}")
        
        # Return 1x1 transparent PNG
        pixel_data = generate_pixel_image()
        return Response(
            content=pixel_data,
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving tracking pixel: {e}")
        # Still return pixel even if logging fails
        pixel_data = generate_pixel_image()
        return Response(content=pixel_data, media_type="image/png")

@router.get("/stats", response_model=TrackingStats)
async def get_tracking_stats():
    """Get email tracking statistics"""
    try:
        df = load_email_opens_data()
        
        if df.empty:
            return TrackingStats(
                total_opens=0,
                unique_users=0,
                total_sent=0,
                open_rate=0.0,
                users_opened=[],
                hourly_distribution={},
                recent_opens=[]
            )
        
        # Calculate stats
        total_opens = len(df)
        unique_users = df['user_email'].nunique()
        
        # Get total sent emails from click logs (if available)
        try:
            click_logs_file = os.path.join(os.path.dirname(get_email_opens_file()), "click_logs.csv")
            if os.path.exists(click_logs_file):
                click_df = pd.read_csv(click_logs_file)
                total_sent = click_df['user_email'].nunique() if not click_df.empty else 0
            else:
                total_sent = unique_users  # Fallback estimate
        except:
            total_sent = unique_users
        
        # Calculate open rate
        open_rate = (unique_users / total_sent * 100) if total_sent > 0 else 0
        
        # Users who opened emails
        users_opened = []
        user_groups = df.groupby('user_email')
        for email, group in user_groups:
            users_opened.append({
                "email": email,
                "open_count": len(group),
                "first_open": group['timestamp'].min().isoformat(),
                "last_open": group['timestamp'].max().isoformat(),
                "unique_actions": group['action_id'].nunique()
            })
        
        # Sort by open count
        users_opened.sort(key=lambda x: x['open_count'], reverse=True)
        
        # Hourly distribution
        df['hour'] = df['timestamp'].dt.hour
        hourly_dist = df.groupby('hour').size().to_dict()
        hourly_distribution = {str(k): v for k, v in hourly_dist.items()}
        
        # Recent opens (last 10)
        recent_opens = []
        recent_df = df.sort_values('timestamp', ascending=False).head(10)
        for _, row in recent_df.iterrows():
            recent_opens.append({
                "email": row['user_email'],
                "action_id": row['action_id'],
                "timestamp": row['timestamp'].isoformat(),
                "ip_address": row['ip_address'],
                "user_agent": row.get('user_agent', 'Unknown')
            })
        
        return TrackingStats(
            total_opens=total_opens,
            unique_users=unique_users,
            total_sent=total_sent,
            open_rate=round(open_rate, 1),
            users_opened=users_opened,
            hourly_distribution=hourly_distribution,
            recent_opens=recent_opens
        )
        
    except Exception as e:
        logger.error(f"Error getting tracking stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving tracking stats: {str(e)}")

@router.get("/export-data")
async def export_tracking_data(
    format: str = Query("csv", description="Export format: csv or json"),
    days: int = Query(30, description="Number of days to include")
):
    """Export email tracking data"""
    try:
        df = load_email_opens_data()
        
        if df.empty:
            return {"message": "No tracking data available"}
        
        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        df_filtered = df[df['timestamp'] >= cutoff_date]
        
        if format.lower() == "json":
            # Convert to JSON
            data = df_filtered.to_dict('records')
            # Convert timestamps to strings
            for record in data:
                if 'timestamp' in record:
                    record['timestamp'] = record['timestamp'].isoformat()
            
            return {
                "export_format": "json",
                "record_count": len(data),
                "date_range_days": days,
                "data": data
            }
        
        else:  # CSV format
            return Response(
                content=df_filtered.to_csv(index=False),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=email_opens_{days}days.csv"}
            )
        
    except Exception as e:
        logger.error(f"Error exporting tracking data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.delete("/clear-data")
async def clear_tracking_data():
    """Clear all email tracking data"""
    try:
        opens_file = get_email_opens_file()
        
        if os.path.exists(opens_file):
            # Create backup
            backup_file = f"{opens_file}.backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            os.rename(opens_file, backup_file)
            
            # Create new empty file
            with open(opens_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "user_email", "action_id", "ip_address", "user_agent", "campaign_id"])
            
            return {
                "message": "Email tracking data cleared successfully",
                "backup_created": backup_file
            }
        else:
            return {"message": "No tracking data file found"}
        
    except Exception as e:
        logger.error(f"Error clearing tracking data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

@router.get("/user-activity/{user_email}")
async def get_user_activity(user_email: str):
    """Get detailed activity for a specific user"""
    try:
        df = load_email_opens_data()
        
        if df.empty:
            return {"message": f"No activity found for {user_email}"}
        
        user_df = df[df['user_email'] == user_email]
        
        if user_df.empty:
            return {"message": f"No activity found for {user_email}"}
        
        activity = []
        for _, row in user_df.iterrows():
            activity.append({
                "timestamp": row['timestamp'].isoformat(),
                "action_id": row['action_id'],
                "ip_address": row['ip_address'],
                "user_agent": row.get('user_agent', 'Unknown'),
                "campaign_id": row.get('campaign_id', '')
            })
        
        return {
            "user_email": user_email,
            "total_opens": len(activity),
            "first_open": activity[0]["timestamp"] if activity else None,
            "last_open": activity[-1]["timestamp"] if activity else None,
            "unique_campaigns": user_df['campaign_id'].nunique(),
            "activity": sorted(activity, key=lambda x: x['timestamp'], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user activity: {str(e)}")

def generate_tracking_id():
    """Generate a unique tracking ID"""
    return f"track-{uuid4().hex[:12]}"

def generate_tracking_url(user_email: str, action_id: str, campaign_id: str = None, base_url: str = "http://localhost:8080"):
    """Generate a tracking pixel URL for an email"""
    tracking_id = generate_tracking_id()
    
    params = [
        f"user_email={user_email}",
        f"action={action_id}"
    ]
    
    if campaign_id:
        params.append(f"campaign={campaign_id}")
    
    return f"{base_url}/track/pixel/{tracking_id}?" + "&".join(params)

def add_tracking_pixel_to_email(email_content: str, tracking_url: str) -> str:
    """Add invisible tracking pixel to email content"""
    # Create tracking pixel HTML
    pixel_html = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="" />'
    
    # Try to insert before closing </body> tag
    if '</body>' in email_content.lower():
        return email_content.replace('</body>', f'{pixel_html}</body>')
    
    # Try to insert before closing </html> tag
    if '</html>' in email_content.lower():
        return email_content.replace('</html>', f'{pixel_html}</html>')
    
    # If no HTML structure, append at the end
    return email_content + pixel_html

@router.post("/test-pixel")
async def test_tracking_pixel(user_email: str = Query(...), action_id: str = Query("test-action")):
    """Test endpoint to generate and test a tracking pixel"""
    try:
        tracking_url = generate_tracking_url(user_email, action_id)
        
        # Create test email content
        test_email = f"""
        <html>
        <body>
        <h2>Test Email</h2>
        <p>This is a test email for {user_email}</p>
        <p>Action ID: {action_id}</p>
        </body>
        </html>
        """
        
        # Add tracking pixel
        email_with_pixel = add_tracking_pixel_to_email(test_email, tracking_url)
        
        return {
            "tracking_url": tracking_url,
            "original_email": test_email,
            "email_with_pixel": email_with_pixel,
            "pixel_added": tracking_url in email_with_pixel,
            "test_note": "Visit the tracking_url to test pixel logging"
        }
        
    except Exception as e:
        logger.error(f"Error testing tracking pixel: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
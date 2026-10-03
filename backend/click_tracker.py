from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from datetime import datetime
import logging
import csv
import os
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

router = APIRouter()

# Setup both file logging and CSV logging
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOG_FILE = os.path.join(DATA_DIR, "click_logs.csv")
TEXT_LOG_FILE = os.path.join(DATA_DIR, "click_logs.txt")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Setup text logging
logging.basicConfig(filename=TEXT_LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize CSV file with headers if it doesn't exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "user_email", "action_id", "ip_address"])

@router.get("/track/click")
def track_click(request: Request, user_email: str, action: str):
    client_ip = request.client.host
    timestamp = datetime.utcnow().isoformat()
    
    # Log to text file
    log_entry = f"{timestamp} - {user_email} - {action} - {client_ip}"
    logging.info(log_entry)
    
    # Log to CSV file
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, user_email, action, client_ip])
    
    # Redirect to training page
    return RedirectResponse(url="/training/phishing-awareness.html")

@router.get("/track/logs")
def get_click_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                logs.append(row)
    return JSONResponse(content=logs)
@router.get("/track/logs/csv")
def download_csv():
    if os.path.exists(LOG_FILE):
        return FileResponse(LOG_FILE, media_type='text/csv', filename="click_logs.csv")
    return JSONResponse(content={"detail": "No log file found"}, status_code=404)

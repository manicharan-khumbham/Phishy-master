import sqlite3
import hashlib
import secrets
import os
import csv
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "phishy.db"

def get_db_connection():
    """Get SQLite database connection with Row factory"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using SHA-256 with salt"""
    if not salt:
        salt = secrets.token_hex(16)
    salted = f"{salt}:{password}".encode('utf-8')
    pw_hash = hashlib.sha256(salted).hexdigest()
    return f"{salt}${pw_hash}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    try:
        if '$' not in stored_hash:
            # Fallback for plain hex hash
            return hashlib.sha256(password.encode('utf-8')).hexdigest() == stored_hash
        salt, pw_hash = stored_hash.split('$', 1)
        salted = f"{salt}:{password}".encode('utf-8')
        return hashlib.sha256(salted).hexdigest() == pw_hash
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def init_db():
    """Initialize SQLite database tables and seed default users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    
    # 2. Click logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_email TEXT NOT NULL,
            action_id TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            referer TEXT
        )
    """)
    
    # 3. Email opens tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_email TEXT NOT NULL,
            action_id TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            campaign_id TEXT
        )
    """)
    
    # 4. Flagged emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flagged_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            email_id TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            flag_category TEXT NOT NULL,
            confidence_level REAL NOT NULL,
            user_email TEXT NOT NULL,
            threat_level TEXT NOT NULL,
            threat_score REAL NOT NULL,
            details TEXT
        )
    """)
    
    conn.commit()
    
    # Seed default admin and initial sample users if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        logger.info("Seeding initial users into SQLite database...")
        now = datetime.now(timezone.utc).isoformat()
        
        default_users = [
            ("admin@phishy.local", hash_password("admin123"), "System Administrator", "admin"),
            ("john.doe@company.com", hash_password("password123"), "John Doe", "user"),
            ("jane.smith@company.com", hash_password("password123"), "Jane Smith", "user"),
            ("alex.security@company.com", hash_password("password123"), "Alex Security Analyst", "analyst")
        ]
        
        for email, pw_hash, full_name, role in default_users:
            cursor.execute("""
                INSERT OR IGNORE INTO users (email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email, pw_hash, full_name, role, now))
        
        conn.commit()
        
    # Migrate any legacy CSV data into SQLite DB
    migrate_csv_data(conn)
    conn.close()
    logger.info("SQLite Database initialized successfully at %s", DB_PATH)

def migrate_csv_data(conn: sqlite3.Connection):
    """Migrate legacy CSV records into SQLite tables if tables are empty"""
    cursor = conn.cursor()
    
    # Click logs CSV
    click_csv = DATA_DIR / "click_logs.csv"
    cursor.execute("SELECT COUNT(*) FROM click_logs")
    if cursor.fetchone()[0] == 0 and click_csv.exists():
        try:
            with open(click_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 4:
                        ts = row[0]
                        email = row[1]
                        action = row[2]
                        ip = row[3]
                        agent = row[4] if len(row) > 4 else None
                        ref = row[5] if len(row) > 5 else None
                        cursor.execute("""
                            INSERT INTO click_logs (timestamp, user_email, action_id, ip_address, user_agent, referer)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (ts, email, action, ip, agent, ref))
            conn.commit()
            logger.info("Migrated click_logs.csv into SQLite DB")
        except Exception as e:
            logger.error(f"Error migrating click_logs CSV: {e}")

    # Email opens CSV
    opens_csv = DATA_DIR / "email_opens.csv"
    cursor.execute("SELECT COUNT(*) FROM email_opens")
    if cursor.fetchone()[0] == 0 and opens_csv.exists():
        try:
            with open(opens_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 4:
                        ts = row[0]
                        email = row[1]
                        action = row[2]
                        ip = row[3]
                        agent = row[4] if len(row) > 4 else None
                        camp = row[5] if len(row) > 5 else None
                        cursor.execute("""
                            INSERT INTO email_opens (timestamp, user_email, action_id, ip_address, user_agent, campaign_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (ts, email, action, ip, agent, camp))
            conn.commit()
            logger.info("Migrated email_opens.csv into SQLite DB")
        except Exception as e:
            logger.error(f"Error migrating email_opens CSV: {e}")

# Helper DB queries
def db_add_click_log(user_email: str, action_id: str, ip_address: str, user_agent: str = None, referer: str = None):
    """Insert click event into SQLite DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO click_logs (timestamp, user_email, action_id, ip_address, user_agent, referer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, user_email, action_id, ip_address, user_agent, referer))
    conn.commit()
    conn.close()

def db_add_email_open(user_email: str, action_id: str, ip_address: str, user_agent: str = None, campaign_id: str = None):
    """Insert email open event into SQLite DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO email_opens (timestamp, user_email, action_id, ip_address, user_agent, campaign_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, user_email, action_id, ip_address, user_agent, campaign_id))
    conn.commit()
    conn.close()

def db_add_flagged_email(email_id: str, sender_email: str, subject: str, flag_category: str, confidence_level: float, user_email: str, threat_level: str, threat_score: float, details: str = None):
    """Insert flagged email event into SQLite DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO flagged_emails (timestamp, email_id, sender_email, subject, flag_category, confidence_level, user_email, threat_level, threat_score, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, email_id, sender_email, subject, flag_category, confidence_level, user_email, threat_level, threat_score, details))
    conn.commit()
    conn.close()

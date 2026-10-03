from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

class SMTPConfig(BaseModel):
    server: str
    port: int
    username: str
    password: str

class EmailSendRequest(BaseModel):
    username: str  # sender's email
    password: str  # app password
    recipient: str
    subject: str
    body: str
    html_body: Optional[str] = None  # HTML version of email
    is_html: Optional[bool] = None  # Auto-detect if not specified
    action_id: Optional[str] = None

class EmailResponse(BaseModel):
    status: str
    message_id: Optional[str] = None
    message: Optional[str] = None
    sent_at: Optional[str] = None

class SMTPTestResponse(BaseModel):
    status: str
    message: str

def get_smtp_config(email: str) -> tuple[str, int]:
    """Auto-detect SMTP server and port based on email domain"""
    domain = email.split('@')[-1].lower()
    
    smtp_configs = {
        'gmail.com': ('smtp.gmail.com', 587),
        'googlemail.com': ('smtp.gmail.com', 587),
        'outlook.com': ('smtp.office365.com', 587),
        'hotmail.com': ('smtp.office365.com', 587),
        'live.com': ('smtp.office365.com', 587),
        'msn.com': ('smtp.office365.com', 587),
        'yahoo.com': ('smtp.mail.yahoo.com', 587),
        'yahoo.co.uk': ('smtp.mail.yahoo.com', 587),
        'yahoo.ca': ('smtp.mail.yahoo.com', 587),
        'ymail.com': ('smtp.mail.yahoo.com', 587),
        'aol.com': ('smtp.aol.com', 587),
        'mail.com': ('smtp.mail.com', 587),
        'icloud.com': ('smtp.mail.me.com', 587),
        'me.com': ('smtp.mail.me.com', 587),
        'protonmail.com': ('127.0.0.1', 1025),  # Requires ProtonMail Bridge
        'zoho.com': ('smtp.zoho.com', 587),
    }
    
    return smtp_configs.get(domain, ('smtp.gmail.com', 587))  # Default to Gmail

@router.post("/send-email", response_model=EmailResponse)
async def send_email(request: EmailSendRequest):
    """
    Send email via auto-detected SMTP server based on sender's email domain
    """
    try:
        # Auto-detect SMTP settings based on email domain
        server, port = get_smtp_config(request.username)
        
        logger.info(f"Auto-detected SMTP: {server}:{port} for {request.username}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = request.subject
        msg['From'] = request.username
        msg['To'] = request.recipient
        msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

        if request.is_html is None:
            # Auto-detect HTML if html_body is provided or body contains HTML tags
            request.is_html = (
                request.html_body is not None or 
                ('<html>' in request.body.lower() and '</html>' in request.body.lower()) or
                ('<p>' in request.body.lower() or '<div>' in request.body.lower())
            )

        html_content = request.html_body if request.html_body else request.body
        plain_content = request.body

        if request.is_html:
            import re
            if request.html_body:
                plain_text = html_content
                plain_text = re.sub(r'</p>', '\n\n', plain_text, flags=re.IGNORECASE)
                plain_text = re.sub(r'<br\s*/?>', '\n', plain_text, flags=re.IGNORECASE)
                plain_text = re.sub(r'</div>', '\n', plain_text, flags=re.IGNORECASE)
                plain_text = re.sub(r'</h[1-6]>', '\n\n', plain_text, flags=re.IGNORECASE)
                plain_text = re.sub('<[^<]+?>', '', plain_text)
                plain_text = plain_text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
                plain_text = plain_text.replace('&amp;', '&').replace('&quot;', '"')
                plain_text = re.sub(r'[ \t]+', ' ', plain_text)
                plain_text = re.sub(r'\n[ \t]+', '\n', plain_text)
                plain_text = re.sub(r'\n{3,}', '\n\n', plain_text)
                plain_text = plain_text.strip()
            else:
                plain_text = plain_content

            plain_part = MIMEText(plain_text, 'plain', 'utf-8')
            msg.attach(plain_part)

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            logger.info(f"Sending HTML email with fallback plain text to {request.recipient}")
        else:
            content_part = MIMEText(plain_content, 'plain', 'utf-8')
            msg.attach(content_part)
            logger.info(f"Sending plain text email to {request.recipient}")

        with smtplib.SMTP(server, port, timeout=30) as smtp_server:
            smtp_server.set_debuglevel(0)  # Set to 1 for debugging
            smtp_server.starttls()
            smtp_server.login(request.username, request.password)
            smtp_server.send_message(msg)

        sent_time = datetime.utcnow().isoformat() + 'Z'
        message_id = f"phishy_{request.action_id or 'manual'}_{hash(request.recipient + request.subject)}"
        
        logger.info(f"Email sent successfully to {request.recipient} via {server}:{port}")
        
        return EmailResponse(
            status="sent",
            message_id=message_id,
            message=f"Email sent successfully to {request.recipient} via {server}",
            sent_at=sent_time
        )

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "failed",
                "message": "SMTP authentication failed. Please check your username and password.",
                "error_type": "authentication"
            }
        )

    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"SMTP recipients refused: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "failed", 
                "message": f"Recipient email address rejected: {request.recipient}",
                "error_type": "recipient"
            }
        )

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "message": f"SMTP server error: {str(e)}",
                "error_type": "smtp"
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "message": f"Failed to send email: {str(e)}",
                "error_type": "unknown"
            }
        )

class SMTPTestRequest(BaseModel):
    username: str
    password: str

@router.post("/test-connection", response_model=SMTPTestResponse)
async def test_smtp_connection(request: SMTPTestRequest):
    """
    Test SMTP connection without sending email - auto-detects server based on email domain
    """
    try:
        server, port = get_smtp_config(request.username)

        logger.info(f"Testing SMTP connection to {server}:{port} with user {request.username}")

        with smtplib.SMTP(server, port, timeout=30) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(request.username, request.password)

        logger.info(f"SMTP test successful for {request.username} on {server}")

        return SMTPTestResponse(
            status="success",
            message=f"SMTP connection successful to {server}:{port} (auto-detected from {request.username.split('@')[-1]})"
        )

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed for {request.username}: {e}")
        return SMTPTestResponse(
            status="failed",
            message="SMTP authentication failed. Please check your email and app password."
        )

    except smtplib.SMTPConnectError as e:
        server, port = get_smtp_config(request.username)
        logger.error(f"SMTP connection failed to {server}:{port}: {e}")
        return SMTPTestResponse(
            status="failed",
            message=f"Cannot connect to SMTP server {server}:{port} (auto-detected)"
        )

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error for {request.username}: {e}")
        return SMTPTestResponse(
            status="failed",
            message=f"SMTP server error: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected SMTP test error for {request.username}: {e}")
        return SMTPTestResponse(
            status="failed",
            message=f"Connection test failed: {str(e)}"
        )

@router.get("/smtp-providers")
async def get_smtp_providers():
    """Get common SMTP provider configurations"""
    return {
        "providers": [
            {
                "name": "Gmail",
                "server": "smtp.gmail.com",
                "port": 587,
                "tls": True,
                "note": "Requires App Password (not regular password)"
            },
            {
                "name": "Outlook/Hotmail",
                "server": "smtp.outlook.com", 
                "port": 587,
                "tls": True,
                "note": "Use your regular email and password"
            },
            {
                "name": "Yahoo",
                "server": "smtp.mail.yahoo.com",
                "port": 587,
                "tls": True,
                "note": "Requires App Password"
            },
            {
                "name": "Custom SMTP",
                "server": "your-smtp-server.com",
                "port": 587,
                "tls": True,
                "note": "Configure with your organization's SMTP settings"
            }
        ]
    }

@router.get("/diagnose/{email}")
async def diagnose_smtp_config(email: str):
    """Diagnose SMTP configuration for a given email address"""
    try:
        domain = email.split('@')[-1].lower()
        server, port = get_smtp_config(email)

        import socket
        connectivity_status = "unknown"
        try:
            socket.create_connection((server, port), timeout=10)
            connectivity_status = "reachable"
        except Exception as e:
            connectivity_status = f"unreachable: {str(e)}"

        return {
            "email": email,
            "domain": domain,
            "smtp_server": server,
            "smtp_port": port,
            "connectivity": connectivity_status,
            "auth_requirements": {
                "gmail.com": "Requires App Password (not regular password)",
                "outlook.com": "Use regular email and password",
                "hotmail.com": "Use regular email and password", 
                "yahoo.com": "Requires App Password",
                "default": "Check with your email provider"
            }.get(domain, "Check with your email provider"),
            "instructions": {
                "gmail.com": [
                    "1. Enable 2-factor authentication",
                    "2. Go to Google Account > Security > App Passwords",
                    "3. Generate app password for 'Mail'",
                    "4. Use the 16-character app password"
                ],
                "outlook.com": [
                    "1. Use your regular email and password",
                    "2. If 2FA enabled, generate app password in security settings"
                ],
                "yahoo.com": [
                    "1. Go to Yahoo Account Security",
                    "2. Generate App Password",
                    "3. Use app password instead of regular password"
                ]
            }.get(domain, ["Check your email provider's SMTP documentation"])
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to diagnose SMTP config: {str(e)}")

@router.get("/health")
async def smtp_health():
    """SMTP service health check"""
    return {
        "status": "healthy",
        "service": "smtp_sender",
        "endpoints": ["/send-email", "/test-connection", "/smtp-providers", "/diagnose/{email}"],
        "version": "2.1.0"
    }
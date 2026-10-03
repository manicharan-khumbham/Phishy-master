from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
import httpx
import logging
from typing import Optional, Dict, Any, List
import json
import asyncio
from pathlib import Path
import re
import base64
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)

class OllamaClient:
    """Enhanced client for interacting with Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "phi3:mini"
        self.timeout = 300.0  # 5 minutes for comprehensive security analysis
        
    async def check_service(self) -> Dict[str, Any]:
        """Check if Ollama service is available and get model info"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
                tags_data = response.json()
                models = tags_data.get("models", [])
                
                phi3_available = any("phi3" in model.get("name", "") for model in models)
                
                return {
                    "service_available": True,
                    "models_available": [model.get("name") for model in models],
                    "phi3_available": phi3_available,
                    "recommended_model": self.model if phi3_available else models[0].get("name") if models else None
                }
                
        except Exception as e:
            logger.warning(f"Ollama service check failed: {e}")
            return {
                "service_available": False,
                "error": str(e),
                "models_available": [],
                "phi3_available": False
            }
    
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate completion using Phi-3 Mini via Ollama"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": 0.9,
                        "stop": ["---END---", "\n\n\n\n"]  # Removed ``` to allow JSON in markdown blocks
                    }
                }
                
                logger.info(f"Sending request to Ollama: {self.model}")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                generated_text = result.get("response", "").strip()
                
                logger.info(f"Generated text length: {len(generated_text)} characters")
                return generated_text
                
        except httpx.TimeoutException:
            logger.error("Ollama API timeout")
            raise HTTPException(status_code=504, detail="LLM service timeout - try reducing complexity or wait for service to respond")
        except httpx.RequestError as e:
            logger.error(f"Ollama API connection error: {e}")
            raise HTTPException(status_code=503, detail="LLM service unavailable - ensure Ollama is running")
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise HTTPException(status_code=500, detail=f"Internal LLM error: {str(e)}")

# Initialize Ollama client
ollama_client = OllamaClient()

# Phishing email scenarios
PHISHING_SCENARIOS = {
    "account_security": {
        "context": "urgent account security notification requiring immediate verification",
        "urgency": "suspicious login detected - immediate action required",
        "threat": "account will be locked if not verified within 24 hours",
        "subject_templates": [
            "Urgent: Suspicious Activity Detected",
            "Security Alert: Verify Your Account",
            "Action Required: Account Security Issue"
        ]
    },
    "payment_issue": {
        "context": "payment processing problem requiring user intervention", 
        "urgency": "payment failure needs immediate resolution",
        "threat": "services may be suspended if payment issue not resolved",
        "subject_templates": [
            "Payment Failed - Action Required",
            "Billing Issue: Update Payment Method",
            "Account Suspension Notice"
        ]
    },
    "system_update": {
        "context": "mandatory system update or policy change",
        "urgency": "compliance deadline approaching",
        "threat": "service disruption if update not completed",
        "subject_templates": [
            "Mandatory System Update Required",
            "Policy Update: Action Required",
            "System Maintenance - Verify Account"
        ]
    },
    "reward_notification": {
        "context": "special offer or reward that expires soon",
        "urgency": "limited time offer expires today",
        "threat": "miss out on exclusive opportunity",
        "subject_templates": [
            "Congratulations! You've Won",
            "Exclusive Offer - Expires Today",
            "Claim Your Reward Now"
        ]
    },
    "it_support": {
        "context": "IT department requesting user action",
        "urgency": "security patch requires immediate installation",
        "threat": "system vulnerability if not patched",
        "subject_templates": [
            "IT Security: Action Required",
            "Critical Security Update",
            "System Patch - Install Now"
        ]
    }
}

def create_phishing_prompt(
    user_email: str, 
    scenario_type: str = "account_security", 
    custom_topic: Optional[str] = None,
    sender_name: Optional[str] = None,
    sender_title: Optional[str] = None,
    sender_department: Optional[str] = None
) -> str:
    """Create dynamic prompts based on user input for personalized phishing emails"""
    
    user_name = user_email.split('@')[0].title()
    domain = user_email.split('@')[1] if '@' in user_email else "company.com"
    company_name = domain.split('.')[0].title()
    
    # Set default sender information if not provided
    if not sender_name:
        sender_name = "Sarah Mitchell"
    if not sender_title:
        sender_title = "Security Administrator"
    if not sender_department:
        sender_department = f"{company_name} IT Security Department"
    
    # Create dynamic prompt based on user inputs
    if custom_topic:
        prompt = f"""Generate a professional business email about "{custom_topic}" to {user_name}.

INSTRUCTIONS:
- Write a realistic business email from {sender_name} ({sender_title}) to {user_name}
- The email topic is: {custom_topic}
- Make it urgent and professional
- Include [CLICK_HERE] placeholder for action link
- Use formal business tone
- Write 3-4 paragraphs with proper structure

EMAIL TEMPLATE:

Subject: [Create urgent subject about {custom_topic}]

Dear {user_name},

I hope this email finds you well. I am {sender_name}, {sender_title} at {sender_department}.

[Write 2-3 sentences about {custom_topic} and why it needs immediate attention]

[Create urgency - explain what happens if they don't act quickly]

To resolve this matter, please click the link below:

[CLICK_HERE]

[Add final urgency statement about time limit]

Thank you for your prompt attention to this matter.

Best regards,

{sender_name}
{sender_title}
{sender_department}
{sender_name.lower().replace(' ', '.')}@{domain} | Phone: (555) 123-4567

GENERATE THE EMAIL NOW:"""
        return prompt
    
    # Use predefined scenario with custom sender
    scenario = PHISHING_SCENARIOS.get(scenario_type, PHISHING_SCENARIOS["account_security"])
    
    prompt = f"""Generate a professional business email about {scenario_type.replace('_', ' ')} to {user_name}.

INSTRUCTIONS:
- Write a realistic business email from {sender_name} ({sender_title}) to {user_name}
- The context is: {scenario['context']}
- Make it urgent: {scenario['urgency']}
- Include [CLICK_HERE] placeholder for action link
- Use formal business tone
- Write 3-4 paragraphs with proper structure

EMAIL TEMPLATE:

Subject: [Create urgent subject about {scenario_type.replace('_', ' ')}]

Dear {user_name},

I hope this email finds you well. I am {sender_name}, {sender_title} at {sender_department}.

{scenario['context']} {scenario['urgency']}

To avoid {scenario['threat']}, please take immediate action by clicking the link below:

[CLICK_HERE]

This must be completed within 24 hours to prevent any service disruption.

Thank you for your prompt attention to this matter.

Best regards,

{sender_name}
{sender_title}
{sender_department}
{sender_name.lower().replace(' ', '.')}@{domain} | Phone: (555) 987-6543

GENERATE THE EMAIL NOW:"""

    return prompt

def generate_fallback_email(user_email: str, action_id: str, link: str, scenario_type: str = "account_security") -> str:
    """Enhanced fallback template when LLM is unavailable"""
    
    scenario = PHISHING_SCENARIOS.get(scenario_type, PHISHING_SCENARIOS["account_security"])
    user_name = user_email.split('@')[0].title()
    domain = user_email.split('@')[1] if '@' in user_email else "company.com"
    
    templates = {
        "account_security": f"""Subject: [URGENT] Security Verification Required - Account Access Suspended

Dear {user_name},

I hope this message finds you well. I am writing to inform you of a critical security matter that requires your immediate attention regarding your {domain} account.

Our advanced threat detection systems have identified multiple unauthorized access attempts on your account from suspicious IP addresses across different geographic locations. These attempts occurred between 2:15 AM and 4:30 AM today, which is outside your typical usage patterns. As part of our enhanced security protocols implemented under Policy SEC-2024-11, we have temporarily restricted certain account functions to protect your sensitive information and prevent potential data breaches.

The security analysis indicates that malicious actors may have obtained partial credential information, possibly through recent phishing campaigns targeting our user base. To ensure the integrity of your account and prevent unauthorized access to your personal data, financial information, and connected services, you must complete our enhanced verification process within the next 24 hours. Failure to complete this verification will result in a full account suspension until identity can be confirmed through our manual review process, which typically takes 5-7 business days.

Please complete the security verification immediately by clicking here: {link}

This secure verification portal will guide you through a brief identity confirmation process and help us restore full access to your account. The process takes approximately 3-5 minutes and includes verification of your contact information and recent account activity. For your security, this link will expire in 24 hours.

Best regards,
Sarah Mitchell
Senior Security Analyst
{domain.split('.')[0].title()} Cybersecurity Operations Center
Phone: +1-800-{domain.split('.')[0].upper()}-SEC
Reference: SEC-{action_id}""",

        "payment_issue": f"""Subject: [ACTION REQUIRED] Payment Processing Failure - Service Interruption Notice

Dear {user_name},

Thank you for being a valued {domain} customer. I am contacting you regarding an urgent billing matter that requires your immediate attention to prevent service disruption.

Our payment processing system attempted to charge your registered payment method for your monthly subscription on {action_id[:8]} but encountered a processing failure. This may be due to an expired card, insufficient funds, changed billing address, or enhanced fraud protection measures implemented by your financial institution. According to our billing policy BP-2024-07, services will be automatically suspended if payment issues are not resolved within 48 hours of initial notification.

Your current subscription includes premium features and cloud storage that will be immediately affected by any service suspension. Additionally, any automated backup processes, scheduled reports, and team collaboration features will be discontinued until payment is successfully processed. Please note that suspended accounts may lose access to certain data recovery options after 72 hours.

To prevent service interruption and maintain access to your account, please update your payment information immediately by visiting our secure billing portal: {link}

Our secure payment system accepts all major credit cards, PayPal, and direct bank transfers. The update process is protected by 256-bit SSL encryption and typically takes 2-3 minutes to complete. Once updated, your services will be automatically restored within 15 minutes.

If you have any questions or need assistance, please contact our billing support team at billing@{domain} or call 1-800-{domain.split('.')[0].upper()}-BILL.

Best regards,
Michael Rodriguez
Senior Billing Specialist
{domain.split('.')[0].title()} Customer Success Team
Billing Reference: BP-{action_id}""",

        "system_update": f"""Subject: {scenario['subject_templates'][0]}

Dear {user_name},

A critical system update requires your immediate attention. All {domain} users must complete this security update by end of day.

Complete the update here: {link}

Failure to complete this update may result in service interruption.

IT Department
{domain.split('.')[0].title()}

Update ID: {action_id}""",
        
        "reward_notification": f"""Subject: {scenario['subject_templates'][0]}

Dear {user_name},

Congratulations! You have been selected for an exclusive {domain.split('.')[0].title()} customer reward program.

Your reward includes:
- Exclusive access to premium features
- 50% discount on services
- Priority customer support

Claim your reward before it expires: {link}

This offer is valid for 48 hours only and is non-transferable.

{domain.split('.')[0].title()} Customer Success Team
Reward Code: {action_id}""",

        "it_support": f"""Subject: {scenario['subject_templates'][0]}

Dear {user_name},

Our IT department has identified a critical security vulnerability that requires immediate patching on all {domain} systems.

URGENT: Please install the security patch by clicking here: {link}

This update must be completed within 2 hours to prevent potential security breaches.

IT Security Team
{domain.split('.')[0].title()}

Patch ID: {action_id}"""
    }
    
    return templates.get(scenario_type, templates["account_security"])

def insert_tracking_url(email_content: str, track_url: str) -> str:
    """
    FIXED: Intelligent tracking URL insertion with multiple fallback strategies
    """
    original_content = email_content
    
    # Strategy 1: Replace common placeholder patterns
    placeholder_patterns = [
        "{{TRACKING_LINK}}",
        "{TRACKING_LINK}",
        "[CLICK_HERE]",
        "[TRACKING_LINK]", 
        "TRACKING_LINK",
        "{{tracking_link}}",
        "{tracking_link}",
        "[tracking_link]",
        "[VERIFICATION_LINK]",
        "[ACTION_LINK]"
    ]
    
    for placeholder in placeholder_patterns:
        if placeholder in email_content:
            email_content = email_content.replace(placeholder, track_url)
            logger.info(f"Replaced placeholder '{placeholder}' with tracking URL")
            return email_content
    
    # Strategy 2: Replace "click here" phrases (case insensitive)
    click_patterns = [
        r'\bclick here\b',
        r'\bclick the link\b',
        r'\bfollowing link\b',
        r'\blink below\b',
        r'\bthis link\b'
    ]
    
    for pattern in click_patterns:
        if re.search(pattern, email_content, re.IGNORECASE):
            email_content = re.sub(
                pattern, 
                lambda m: f"{m.group()}: {track_url}",
                email_content, 
                flags=re.IGNORECASE,
                count=1  # Only replace the first occurrence
            )
            logger.info(f"Enhanced 'click here' pattern with tracking URL")
            return email_content
    
    # Strategy 3: Find "verify" or "update" and insert link after
    action_patterns = [
        (r'(verify[^.]*)', f'\\1\n\nVerification Link: {track_url}'),
        (r'(update[^.]*)', f'\\1\n\nUpdate Link: {track_url}'),
        (r'(complete[^.]*)', f'\\1\n\nCompletion Link: {track_url}'),
        (r'(secure[^.]*)', f'\\1\n\nSecure Access: {track_url}'),
        (r'(login[^.]*)', f'\\1\n\nLogin Here: {track_url}')
    ]
    
    for pattern, replacement in action_patterns:
        if re.search(pattern, email_content, re.IGNORECASE):
            email_content = re.sub(
                pattern, 
                replacement,
                email_content, 
                flags=re.IGNORECASE,
                count=1
            )
            logger.info(f"Inserted tracking URL after action word")
            return email_content
    
    # Strategy 4: Insert before signature (look for common signature patterns)
    signature_patterns = [
        r'(Best regards,)',
        r'(Sincerely,)',
        r'(Thank you,)',
        r'(IT Department)',
        r'(Security Team)',
        r'(\w+ Team)'
    ]
    
    for pattern in signature_patterns:
        if re.search(pattern, email_content, re.IGNORECASE):
            email_content = re.sub(
                pattern,
                f'Take Action: {track_url}\n\n\\1',
                email_content,
                flags=re.IGNORECASE,
                count=1
            )
            logger.info(f"Inserted tracking URL before signature")
            return email_content
    
    # Strategy 5: Last resort - append at the end
    if track_url not in email_content:
        email_content += f"\n\nAction Required: {track_url}"
        logger.warning("Used fallback: appended tracking URL at end")
    
    return email_content

def generate_tracking_id():
    """Generate a unique tracking ID"""
    return f"track-{uuid4().hex[:12]}"

def generate_tracking_url(user_email: str, action_id: str, campaign_id: str = None, base_url: str = None):
    """Generate a tracking pixel URL for an email"""
    import os
    # Use environment variable or provided base_url, fallback to localhost
    if base_url is None:
        base_url = os.getenv("BASE_URL", "http://localhost:8080")
    
    tracking_id = generate_tracking_id()
    
    params = [
        f"user_email={user_email}",
        f"action={action_id}"
    ]
    
    if campaign_id:
        params.append(f"campaign={campaign_id}")
    
    return f"{base_url}/email-track/pixel/{tracking_id}?" + "&".join(params)

def convert_to_html_email(email_content: str) -> str:
    """Convert plain text email to professional HTML format with better business styling"""
    lines = email_content.split('\n')
    html_lines = []
    
    in_body = False
    in_signature = False
    
    for line in lines:
        line = line.strip()
        
        # Handle empty lines - they indicate paragraph breaks
        if not line:
            if in_body and not in_signature:
                html_lines.append('<br><br>')  # Double break for paragraph spacing
            continue
            
        # Handle subject line
        if line.startswith('Subject:'):
            subject = line.replace('Subject:', '').strip()
            continue
            
        # Handle greeting
        if line.startswith('Dear '):
            in_body = True
            html_lines.append(f'<p style="margin-bottom: 20px; font-weight: 600; color: #2c3e50;">{line}</p>')
            continue
            
        # Handle signature section
        if any(closing in line.lower() for closing in ['best regards', 'sincerely', 'thank you']):
            in_signature = True
            html_lines.append('<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e1e5e9;">')
            html_lines.append(f'<p style="margin-bottom: 15px; font-weight: 600; color: #34495e;">{line}</p>')
            continue
            
        # Handle content in body
        if in_body:
            if in_signature:
                # Signature lines (name, title, company, contact)
                if len(line) < 80 and not line.endswith('.'):
                    if '@' in line or 'phone' in line.lower() or line.startswith('+'):
                        # Contact information
                        html_lines.append(f'<p style="margin: 2px 0; color: #7f8c8d; font-size: 13px;">{line}</p>')
                    else:
                        # Name and title
                        html_lines.append(f'<p style="margin: 2px 0; color: #2c3e50; font-weight: 500;">{line}</p>')
                else:
                    html_lines.append(f'<p style="margin: 8px 0; color: #34495e;">{line}</p>')
            else:
                # Main body content
                if '[CLICK_HERE]' in line:
                    # Call-to-action line
                    html_lines.append(f'<div style="margin: 25px 0; text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">')
                    html_lines.append(f'<p style="margin: 0; font-weight: 600; color: #2c3e50;">{line}</p>')
                    html_lines.append('</div>')
                else:
                    # Break long paragraphs into sentences for better readability
                    if len(line) > 150:  # Long paragraph
                        sentences = line.replace('. ', '.\n').split('\n')
                        for sentence in sentences:
                            if sentence.strip():
                                html_lines.append(f'<p style="margin-bottom: 12px; line-height: 1.6; color: #34495e;">{sentence.strip()}</p>')
                    else:
                        # Regular paragraph
                        html_lines.append(f'<p style="margin-bottom: 16px; line-height: 1.6; color: #34495e;">{line}</p>')
    
    # Close signature div if it was opened
    if in_signature:
        html_lines.append('</div>')
    
    # Professional HTML structure with better styling
    html_email = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Important Notice</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f7fa;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f7fa; padding: 40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                    <tr>
                        <td style="padding: 40px 30px; font-size: 16px; line-height: 1.6;">
                            {''.join(html_lines)}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html_email

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

class EmailGenRequest(BaseModel):
    user_email: str = Field(..., description="Target user email address")
    scenario_type: Optional[str] = Field("account_security", description="Type of phishing scenario")
    custom_topic: Optional[str] = Field(None, description="Custom topic for flexible email generation - overrides scenario_type")
    sender_name: Optional[str] = Field(None, description="Name of the email sender")
    sender_title: Optional[str] = Field(None, description="Title/position of the email sender")
    sender_department: Optional[str] = Field(None, description="Department of the email sender")
    use_llm: Optional[bool] = Field(True, description="Whether to use LLM for generation")
    include_tracking_pixel: Optional[bool] = Field(True, description="Whether to include tracking pixel for email opens")
    html_format: Optional[bool] = Field(True, description="Whether to generate HTML formatted email")
    campaign_id: Optional[str] = Field(None, description="Campaign ID for tracking purposes")
    temperature: Optional[float] = Field(0.7, ge=0.1, le=1.0, description="LLM creativity level")
    max_tokens: Optional[int] = Field(300, ge=50, le=500, description="Maximum tokens for LLM generation")

class EmailResponse(BaseModel):
    email: str
    action_id: str
    track_url: str
    tracking_pixel_url: Optional[str] = None
    email_content: str
    email_content_with_pixel: Optional[str] = None
    email_content_html: Optional[str] = None
    email_content_html_with_pixel: Optional[str] = None
    generated_at: str
    generation_method: str
    scenario_type: str
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None

# NEW: General Chat Classes and Endpoint
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message for general chat")
    temperature: Optional[float] = Field(0.7, ge=0.1, le=1.0, description="LLM creativity level")
    max_tokens: Optional[int] = Field(500, ge=50, le=1000, description="Maximum tokens for response")

class ChatResponse(BaseModel):
    response: str
    model_used: str
    generation_time_ms: int
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
async def general_chat(request: ChatRequest):
    """
    General chat endpoint with smart data integration
    
    Allows users to have conversations with Phi-3 Mini as Phishy with access to real data.
    """
    start_time = datetime.utcnow()
    
    try:
        # Check if this is a data-related query that needs real information
        query_lower = request.message.lower()
        needs_real_data = any(keyword in query_lower for keyword in [
            "who clicked", "recent clicks", "users who", "fell for", "simulation", 
            "recent activity", "click data", "user data", "which users", "cllicked",
            "most recent users", "5 most recent", "recent 5", "security status",
            "our simulation", "simulation trap", "recent user clicks", "recent users",
            "user before", "before that", "next user", "previous user", "other users",
            "who else", "what about", "second user", "third user", "list users",
            "show me", "tell me about", "more users", "other clicks", "which user",
            "most recent user", "recently fell", "user most recently", "most recently",
            "recent user", "latest user", "last user", "newest victim", "latest victim"
        ]) or ("user" in query_lower and ("recent" in query_lower or "latest" in query_lower or "last" in query_lower))
        
        logger.info(f"Processing chat request: '{request.message}' - Data query detected: {needs_real_data}")
        
        if needs_real_data:
            logger.info(f"🎯 SMART DATA QUERY DETECTED: {request.message}")
            # Import and use smart query handler for data queries
            try:
                from .smart_query_handler import SmartQueryAnalyzer
                analyzer = SmartQueryAnalyzer()
                
                # Analyze the query intent
                intent = analyzer.analyze_query_intent(request.message)
                logger.info(f"Query intent: {intent}")
                
                # Always fetch data for detected queries (not just specific intent types)
                recent_clicks = analyzer.data_fetcher.get_recent_clicks(hours=24*30, limit=20)  # Last 30 days
                user_activity = analyzer.data_fetcher.get_user_activity_summary(days=30)
                data = {
                    "recent_clicks": recent_clicks,
                    "user_activity": user_activity
                }
                logger.info(f"Fetched {len(recent_clicks)} recent clicks, {user_activity['total_users']} total users")
                
                # Create schema-aware data summary for LLM
                data_summary = ""
                if not data["recent_clicks"].empty:
                    recent_df = data["recent_clicks"].head(5)  # Limit to 5 for simplicity
                    
                    # Add schema information first
                    data_summary = """DATA SCHEMA:
Each record represents one user clicking on a phishing simulation email.
Fields: timestamp, user_email, action_id, ip_address, user_agent, referer

RECENT SIMULATION VICTIMS (most recent first):
"""
                    
                    for idx, row in recent_df.iterrows():
                        time_ago = datetime.utcnow() - pd.to_datetime(row['timestamp'])
                        
                        if time_ago.total_seconds() < 86400:  # Less than 1 day
                            time_desc = "today"
                        else:
                            days = int(time_ago.total_seconds() / 86400)
                            time_desc = f"{days} days ago"
                        
                        position = idx + 1
                        # Include more schema context
                        data_summary += f"{position}. User: {row['user_email']} | When: {time_desc} | Action: {row['action_id']}\n"
                    
                    # Schema-aware summary
                    most_recent = recent_df.iloc[0]
                    total_victims = len(data["user_activity"]["users"])
                    data_summary += f"\nSUMMARY:\n"
                    data_summary += f"- Most recent victim: {most_recent['user_email']}\n"
                    data_summary += f"- Total victims in database: {total_victims}\n"
                    data_summary += f"- Each 'click' = one user falling for a phishing email simulation\n"
                else:
                    data_summary = "No recent simulation victims found in the click_logs database.\n"
                
                # Create schema-aware prompt with real data
                prompt = f"""You are Phishy, a cybersecurity assistant analyzing phishing simulation data.

Question: {request.message}

{data_summary}

CONTEXT:
- This data comes from click_logs.csv which tracks users who fell for phishing simulations
- Each row = one user clicking on a simulated phishing email  
- timestamp = when they clicked
- user_email = the victim's email address
- action_id = unique identifier for the phishing campaign they fell for

Instructions:
- Answer using only the real data provided above
- When asked "who clicked recently" refer to the most recent victim
- When asked "user before that" refer to the 2nd in the list
- Be factual and concise

Answer:"""

            except Exception as e:
                logger.warning(f"Smart query failed: {e}, falling back to standard chat")
                prompt = f"""You are an expert cybersecurity assistant. The user asked: {request.message}

Unfortunately, I cannot access the real-time click data right now, but I can provide general cybersecurity guidance. How can I help you with cybersecurity concepts or best practices?"""
        
        else:
            # Standard educational prompt for non-data queries
            prompt = f"""You are Phishy, an expert cybersecurity assistant. Your role is to provide helpful, educational responses about cybersecurity.

When answering questions:
- Provide clear, practical explanations
- Include specific examples when relevant
- Focus on helping users understand concepts
- Use conversational, professional language
- For greetings, respond naturally and ask how you can help

User question: {request.message}

Please provide a helpful response:"""
        
        # Generate response using Phi-3 Mini via Ollama with optimized settings
        if needs_real_data:
            # Use more conservative settings for data queries
            llm_response = await ollama_client.generate_completion(
                prompt, 
                max_tokens=150,  # Shorter for more focused responses
                temperature=0.1  # Very low temperature for factual responses
            )
        else:
            # Use normal settings for general chat
            llm_response = await ollama_client.generate_completion(
                prompt, 
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
        
        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(f"Successfully generated chat response using {ollama_client.model}")
        
        return ChatResponse(
            response=llm_response.strip(),
            model_used=ollama_client.model,
            generation_time_ms=generation_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        # If LLM fails or is unavailable, provide a helpful fallback response
        logger.warning(f"LLM chat failed: {e}")
        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return ChatResponse(
            response=f"Hi! I'm Phishy, your AI cybersecurity assistant. I'm sorry, but I'm having trouble connecting to my AI service right now. However, I can still help you generate phishing emails for training, analyze security data, or provide system information. Please try asking about cybersecurity topics, phishing simulation, or check if Ollama is running properly with Phi-3 Mini.",
            model_used="fallback",
            generation_time_ms=generation_time,
            timestamp=datetime.utcnow().isoformat()
        )

@router.post("/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailGenRequest):
    """
    FIXED: Generate phishing simulation email using Phi-3 Mini or fallback template
    
    Creates realistic phishing emails for security awareness training with various scenarios or custom topics.
    """
    
    start_time = datetime.utcnow()
    user_email = request.user_email
    action_id = f"phish-{uuid4().hex[:8]}"
    
    # Use environment variable for base URL
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:8080")
    track_url = f"{base_url}/track/click?user_email={user_email}&action={action_id}"
    
    generation_method = "fallback"
    email_content = ""
    model_used = None
    
    # Validate scenario type only if no custom topic is provided
    if not request.custom_topic and request.scenario_type not in PHISHING_SCENARIOS:
        available_scenarios = list(PHISHING_SCENARIOS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario_type. Available options: {available_scenarios}, or provide a custom_topic"
        )
    
    if request.use_llm:
        try:
            # Generate using Phi-3 Mini via Ollama with custom topic and sender support
            prompt = create_phishing_prompt(
                user_email, 
                request.scenario_type, 
                request.custom_topic,
                request.sender_name,
                request.sender_title,
                request.sender_department
            )
            llm_response = await ollama_client.generate_completion(
                prompt, 
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # FIXED: Use the intelligent tracking URL insertion function
            email_content = insert_tracking_url(llm_response, track_url)
            generation_method = "phi3_mini_ollama"
            model_used = ollama_client.model
            
            logger.info(f"Successfully generated email using {model_used} for {user_email}")
            
        except HTTPException:
            # Re-raise HTTP exceptions (these are already properly formatted)
            raise
        except Exception as e:
            # If LLM fails for other reasons, use fallback
            logger.warning(f"LLM generation failed for {user_email}: {e}")
            email_content = generate_fallback_email(user_email, action_id, track_url, request.scenario_type)
            generation_method = "fallback_template"
    else:
        # Explicitly requested fallback
        email_content = generate_fallback_email(user_email, action_id, track_url, request.scenario_type)
        generation_method = "fallback_template"
    
    generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    # Generate HTML versions if requested
    email_content_html = None
    email_content_html_with_pixel = None
    
    if request.html_format:
        try:
            email_content_html = convert_to_html_email(email_content)
            logger.info(f"Generated HTML version for {user_email}")
        except Exception as e:
            logger.error(f"Failed to generate HTML for {user_email}: {e}")
    
    # Generate tracking pixel if requested
    tracking_pixel_url = None
    email_content_with_pixel = None
    
    if request.include_tracking_pixel:
        try:
            tracking_pixel_url = generate_tracking_url(
                user_email, 
                action_id, 
                request.campaign_id
            )
            email_content_with_pixel = add_tracking_pixel_to_email(email_content, tracking_pixel_url)
            
            # Also add pixel to HTML version if available
            if email_content_html:
                email_content_html_with_pixel = add_tracking_pixel_to_email(email_content_html, tracking_pixel_url)
                
            logger.info(f"Added tracking pixel to email for {user_email}")
        except Exception as e:
            logger.warning(f"Failed to add tracking pixel: {e}")
            email_content_with_pixel = email_content
    
    return EmailResponse(
        email=user_email,
        action_id=action_id,
        track_url=track_url,
        tracking_pixel_url=tracking_pixel_url,
        email_content=email_content,
        email_content_with_pixel=email_content_with_pixel,
        email_content_html=email_content_html,
        email_content_html_with_pixel=email_content_html_with_pixel,
        generated_at=datetime.utcnow().isoformat(),
        generation_method=generation_method,
        scenario_type=request.custom_topic or request.scenario_type,
        model_used=model_used,
        generation_time_ms=generation_time
    )

# NEW: Debug endpoint to test tracking URL insertion
@router.post("/debug-tracking")
async def debug_tracking_insertion(
    user_email: str = Query(..., description="Target email address"),
    scenario_type: str = Query("system_update", description="Scenario type"),
    custom_topic: Optional[str] = Query(None, description="Custom topic")
):
    """
    Debug endpoint to test tracking URL insertion specifically
    """
    action_id = f"debug-{uuid4().hex[:8]}"
    track_url = f"http://localhost:8080/track/click?user_email={user_email}&action={action_id}"
    
    debug_info = {
        "input": {
            "user_email": user_email,
            "scenario_type": scenario_type,
            "custom_topic": custom_topic,
            "generated_tracking_url": track_url
        },
        "steps": []
    }
    
    try:
        # Generate with LLM
        prompt = create_phishing_prompt(user_email, scenario_type, custom_topic)
        llm_response = await ollama_client.generate_completion(prompt, max_tokens=300)
        
        debug_info["llm_raw_response"] = llm_response
        debug_info["steps"].append("Generated raw LLM response")
        
        # Test tracking URL insertion
        final_email = insert_tracking_url(llm_response, track_url)
        
        debug_info["final_email"] = final_email
        debug_info["tracking_url_inserted"] = track_url in final_email
        debug_info["insertion_successful"] = final_email != llm_response
        debug_info["steps"].append("Applied tracking URL insertion")
        
        # Show what changed
        if final_email != llm_response:
            debug_info["changes_made"] = "Tracking URL successfully inserted"
        else:
            debug_info["changes_made"] = "No changes - URL insertion may have failed"
            
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["fallback_test"] = generate_fallback_email(user_email, action_id, track_url, scenario_type)
        debug_info["fallback_has_url"] = track_url in debug_info["fallback_test"]
    
    return debug_info

# NEW: Flexible Email Generation Endpoint
@router.post("/generate-flexible-email")
async def generate_flexible_email(
    user_email: str = Query(..., description="Target email address"),
    topic: str = Query(..., description="Any topic for the phishing email"),
    temperature: float = Query(0.7, description="Creativity level"),
    max_tokens: int = Query(300, description="Maximum response length")
):
    """
    Generate phishing email for ANY topic - completely flexible
    
    Examples:
    - "COVID-19 vaccine appointment"
    - "Free pizza in the break room"
    - "New parking regulations"
    - "Employee satisfaction survey"
    - "Mandatory compliance training"
    - "Company merger announcement"
    """
    
    try:
        request = EmailGenRequest(
            user_email=user_email,
            custom_topic=topic,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return await generate_email(request)
            
    except Exception as e:
        logger.error(f"Flexible email generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.get("/health")
async def check_llm_health():
    """
    Comprehensive health check for LLM service
    """
    try:
        service_status = await ollama_client.check_service()
        
        # Test generation if service is available
        if service_status["service_available"]:
            try:
                test_prompt = "Generate a brief test response saying 'Service OK' and nothing else."
                test_response = await asyncio.wait_for(
                    ollama_client.generate_completion(test_prompt, max_tokens=10),
                    timeout=15.0
                )
                service_status["generation_test"] = {
                    "success": True,
                    "response_preview": test_response[:50] + "..." if len(test_response) > 50 else test_response
                }
            except Exception as e:
                service_status["generation_test"] = {
                    "success": False,
                    "error": str(e)
                }
        
        status_code = 200 if service_status["service_available"] else 503
        
        return JSONResponse(content={
            "status": "healthy" if service_status["service_available"] else "degraded",
            "ollama_service": service_status,
            "fallback_available": True,
            "supported_scenarios": list(PHISHING_SCENARIOS.keys()),
            "custom_topics_supported": True,
            "tracking_url_insertion": "enhanced_with_multiple_strategies",
            "checked_at": datetime.utcnow().isoformat()
        }, status_code=status_code)
        
    except Exception as e:
        return JSONResponse(content={
            "status": "unhealthy",
            "error": str(e),
            "fallback_available": True,
            "checked_at": datetime.utcnow().isoformat()
        }, status_code=500)

@router.get("/scenarios")
def get_available_scenarios():
    """
    Get list of available phishing scenarios
    """
    scenarios_info = {}
    for scenario_name, scenario_data in PHISHING_SCENARIOS.items():
        scenarios_info[scenario_name] = {
            "name": scenario_name.replace('_', ' ').title(),
            "description": scenario_data["context"],
            "urgency_factor": scenario_data["urgency"],
            "threat_element": scenario_data["threat"],
            "sample_subjects": scenario_data["subject_templates"][:2]  # Show first 2 templates
        }
    
    return JSONResponse(content={
        "available_scenarios": scenarios_info,
        "total_scenarios": len(PHISHING_SCENARIOS),
        "usage_tip": "Use the scenario_type parameter in /generate-email to specify which scenario to use, or use custom_topic for unlimited flexibility"
    })

@router.post("/test-generation")
async def test_generation(
    scenario_type: str = Query("account_security", description="Scenario to test"),
    custom_topic: Optional[str] = Query(None, description="Custom topic to test"),
    use_llm: bool = Query(True, description="Test LLM or fallback")
):
    """
    Test email generation without creating tracking links
    
    Useful for testing different scenarios and LLM connectivity.
    """
    if not custom_topic and scenario_type not in PHISHING_SCENARIOS:
        available_scenarios = list(PHISHING_SCENARIOS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario_type. Available options: {available_scenarios}, or provide custom_topic"
        )
    
    test_email = "test.user@example.com"
    test_action = "test-action-123"
    test_link = "https://example.com/training"
    
    start_time = datetime.utcnow()
    
    if use_llm:
        try:
            prompt = create_phishing_prompt(test_email, scenario_type, custom_topic)
            response = await ollama_client.generate_completion(prompt, max_tokens=300)
            email_content = insert_tracking_url(response, test_link)
            method = "phi3_mini_ollama"
        except Exception as e:
            email_content = generate_fallback_email(test_email, test_action, test_link, scenario_type)
            method = f"fallback_due_to_error: {str(e)}"
    else:
        email_content = generate_fallback_email(test_email, test_action, test_link, scenario_type)
        method = "fallback_template"
    
    generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    return {
        "test_result": "success",
        "scenario_type": custom_topic or scenario_type,
        "generation_method": method,
        "generation_time_ms": generation_time,
        "email_content": email_content,
        "tracking_url_present": test_link in email_content,
        "note": "This is a test generation - no tracking links were created"
    }

class BatchEmailRequest(BaseModel):
    user_emails: List[str] = Field(..., description="List of user emails")
    scenario_type: Optional[str] = Field("account_security", description="Scenario type for all emails")
    custom_topic: Optional[str] = Field(None, description="Custom topic for all emails")
    use_llm: bool = Field(True, description="Whether to use LLM")
    max_concurrent: int = Field(5, ge=1, le=10, description="Maximum concurrent generations")

@router.post("/batch-generate")
async def batch_generate_emails(request: BatchEmailRequest):
    """
    Generate multiple phishing emails at once
    
    Useful for creating campaigns targeting multiple users with the same scenario or custom topic.
    """
    if len(request.user_emails) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 emails per batch")
    
    if not request.custom_topic and request.scenario_type not in PHISHING_SCENARIOS:
        available_scenarios = list(PHISHING_SCENARIOS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario_type. Available options: {available_scenarios}, or provide custom_topic"
        )
    
    results = []
    semaphore = asyncio.Semaphore(request.max_concurrent)
    
    async def generate_single_email(email: str):
        async with semaphore:
            try:
                email_request = EmailGenRequest(
                    user_email=email,
                    scenario_type=request.scenario_type,
                    custom_topic=request.custom_topic,
                    use_llm=request.use_llm
                )
                response = await generate_email(email_request)
                return {
                    "email": email,
                    "success": True,
                    "result": response.model_dump()
                }
            except Exception as e:
                return {
                    "email": email,
                    "success": False,
                    "error": str(e)
                }
    
    # Execute batch generation
    tasks = [generate_single_email(email) for email in request.user_emails]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    
    return {
        "batch_summary": {
            "total_requested": len(request.user_emails),
            "successful": len(successful),
            "failed": len(failed),
            "topic": request.custom_topic or request.scenario_type,
            "used_llm": request.use_llm
        },
        "results": results,
        "generated_at": datetime.utcnow().isoformat()
    }

class CustomScenarioRequest(BaseModel):
    scenario_name: str = Field(..., description="Unique name for the scenario")
    context: str = Field(..., description="Scenario context description")
    urgency: str = Field(..., description="Urgency factor for the scenario")
    threat: str = Field(..., description="Threat element of the scenario")
    subject_templates: List[str] = Field(..., description="List of subject line templates")

@router.post("/customize-scenario")
async def create_custom_scenario(request: CustomScenarioRequest):
    """
    Create a custom phishing scenario
    
    Note: In production, this would save to a database. Currently stores in memory only.
    """
    if len(request.subject_templates) < 1:
        raise HTTPException(status_code=400, detail="At least one subject template is required")
    
    if request.scenario_name in PHISHING_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Scenario '{request.scenario_name}' already exists")
    
    # Add to scenarios (temporary - would be saved to DB in production)
    PHISHING_SCENARIOS[request.scenario_name] = {
        "context": request.context,
        "urgency": request.urgency,
        "threat": request.threat,
        "subject_templates": request.subject_templates,
        "custom": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": f"Custom scenario '{request.scenario_name}' created successfully",
        "scenario": PHISHING_SCENARIOS[request.scenario_name],
        "total_scenarios": len(PHISHING_SCENARIOS),
        "note": "Custom scenarios are stored in memory and will be lost on server restart"
    }

@router.get("/generation-stats")
def get_generation_stats():
    """
    Get statistics about email generation
    
    In production, this would query actual usage data from a database.
    """
    # This is a placeholder - in production you'd track actual usage
    return {
        "available_scenarios": len(PHISHING_SCENARIOS),
        "scenario_types": list(PHISHING_SCENARIOS.keys()),
        "fallback_templates_available": True,
        "custom_topics_supported": True,
        "tracking_url_insertion": "enhanced_with_intelligent_fallbacks",
        "llm_integration": {
            "model": ollama_client.model,
            "base_url": ollama_client.base_url,
            "timeout": ollama_client.timeout
        },
        "features": {
            "batch_generation": True,
            "custom_scenarios": True,
            "health_monitoring": True,
            "fallback_mode": True,
            "general_chat": True,
            "unlimited_topics": True,
            "flexible_generation": True,
            "intelligent_url_insertion": True,
            "debug_endpoints": True
        }
    }

class SecurityAnalysisRequest(BaseModel):
    """Request model for AI security analysis explanation"""
    analysis_results: Dict[str, Any] = Field(..., description="Comprehensive security analysis results")
    email_content: Optional[str] = Field(None, description="Original email content")
    user_id: str = Field(..., description="User ID for tracking")
    prompt: Optional[str] = Field(None, description="Custom prompt for LLM")

@router.post("/explain-security-analysis")
async def explain_security_analysis(request: SecurityAnalysisRequest):
    """
    Generate an explainable AI summary of comprehensive security analysis results.
    
    This endpoint combines ML, API, and pattern analysis results to provide
    clear, actionable explanations for end users. NO FALLBACKS - LLM must be available.
    """
    logger.info(f"🤖 Generating security explanation for user {request.user_id}")
    
    # Check Ollama service availability - FAIL if unavailable
    service_status = await ollama_client.check_service()
    if not service_status["service_available"]:
        logger.error("Ollama service unavailable - no fallback allowed")
        raise HTTPException(status_code=503, detail="AI service unavailable. Local LLM is required for security explanations.")
    
    # Build comprehensive prompt
    prompt = request.prompt or build_default_security_prompt(request.analysis_results)
    
    # Generate explanation using LLM - FAIL if unsuccessful
    llm_response = await ollama_client.generate_completion(prompt, max_tokens=1000, temperature=0.3)
    
    if not llm_response or len(llm_response.strip()) < 10:
        logger.error("LLM returned empty or invalid response")
        raise HTTPException(status_code=500, detail="AI model failed to generate explanation")
    
    # Parse LLM response (expecting JSON format) - FAIL if invalid
    try:
        # Extract JSON from markdown if present
        json_content = extract_json_from_response(llm_response)
        explanation = json.loads(json_content)
        
        # Validate required fields - FAIL if missing
        required_fields = ["summary", "overall_risk_level", "key_findings", "recommendations"]
        if not all(field in explanation for field in required_fields):
            logger.error("LLM response missing required fields")
            raise HTTPException(status_code=500, detail="AI model returned incomplete explanation")
            
        logger.info(f"✅ Generated security explanation with {len(explanation.get('key_findings', []))} findings")
        return explanation
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM response not valid JSON: {e} - Original response: {llm_response[:200]}...")
        raise HTTPException(status_code=500, detail="AI model returned invalid response format")
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e} - Original response: {llm_response[:200]}...")
        raise HTTPException(status_code=500, detail="AI model returned unparseable response")

def extract_json_from_response(response: str) -> str:
    """Extract JSON content from LLM response that may be wrapped in markdown"""
    response = response.strip()
    
    # Look for JSON in markdown code blocks
    import re
    json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    matches = re.findall(json_pattern, response, re.DOTALL | re.IGNORECASE)
    
    if matches:
        # Use the first JSON block found
        json_content = matches[0].strip()
        logger.info(f"Extracted JSON from markdown block: {len(json_content)} characters")
        return json_content
    
    # Look for JSON object directly (starts with { and ends with })
    json_pattern = r'\{.*\}'
    matches = re.findall(json_pattern, response, re.DOTALL)
    
    if matches:
        # Use the last complete JSON object found (in case there are incomplete ones)
        json_content = matches[-1].strip()
        logger.info(f"Extracted JSON object directly: {len(json_content)} characters")
        return json_content
    
    # If no JSON found, return original response and let JSON parser handle the error
    logger.warning("No JSON content found in LLM response")
    return response

def build_default_security_prompt(analysis_results: Dict[str, Any]) -> str:
    """Build a comprehensive prompt for security analysis explanation"""
    
    ml_analysis = analysis_results.get("ml_analysis", {})
    safe_browsing = analysis_results.get("safe_browsing", {})
    urlscan_io = analysis_results.get("urlscan_io", {})
    path_intelligence = analysis_results.get("path_intelligence", {})
    
    return f"""You are an expert cybersecurity analyst explaining email security analysis to end users.

ANALYSIS RESULTS TO EXPLAIN:

ML ANALYSIS:
- Is Phishing: {ml_analysis.get('is_phishing', 'Unknown')}
- Confidence: {ml_analysis.get('confidence_score', 0)}%
- Risk Level: {ml_analysis.get('risk_level', 'Unknown')}

GOOGLE SAFE BROWSING:
- Status: {safe_browsing.get('status', 'Unknown')}
- URLs Checked: {safe_browsing.get('urls_checked', 0)}
- Threats Found: {len(safe_browsing.get('threats', []))}

URLSCAN.IO:
- Status: {urlscan_io.get('status', 'Unknown')}
- Malicious Score: {urlscan_io.get('malicious_score', 0)}/100
- URLs Scanned: {urlscan_io.get('urls_scanned', 0)}

PATH INTELLIGENCE:
- Suspicious Patterns: {path_intelligence.get('hasPathThreats', False)}
- Pattern Warnings: {len(path_intelligence.get('pathWarnings', []))}
- URLs Analyzed: {path_intelligence.get('analysisMetrics', {}).get('urlsAnalyzed', 0)}

Provide a clear explanation in this EXACT JSON format:
{{
  "summary": "2-3 sentence explanation of what this email is and why it's dangerous/safe",
  "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "key_findings": ["Specific finding 1", "Specific finding 2", "Specific finding 3"],
  "recommendations": ["Action user should take 1", "Action user should take 2", "Action user should take 3"]
}}

FOCUS ON:
1. Explaining WHY different tools gave different results (if they disagree)
2. What attack techniques are being used (cloud storage abuse, URL evasion, etc.)
3. Clear, actionable advice in simple language
4. Why this is a sophisticated attack if patterns were detected but APIs say clean

Be direct and clear. Avoid technical jargon."""


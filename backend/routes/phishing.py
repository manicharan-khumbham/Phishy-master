from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_phishing_email(email: str, action_id: str, link: str, template_type: str = "security") -> str:
    """Generate basic phishing email templates"""
    
    user_name = email.split('@')[0].title()
    domain = email.split('@')[1] if '@' in email else "company.com"
    company_name = domain.split('.')[0].title()
    
    templates = {
        "security": f"""Subject: Security Alert: Immediate Action Required

Dear {user_name},

We have detected suspicious activity on your {company_name} account. For your security, we need you to verify your account information immediately.

Suspicious activity detected:
- Multiple failed login attempts
- Access from unrecognized device
- Unusual location: Unknown IP address

Please click the following link to secure your account:
{link}

If you do not take action within 24 hours, your account may be temporarily suspended as a security precaution.

Thank you for your prompt attention to this matter.

Best regards,
{company_name} Security Team

Reference ID: {action_id}

---
This is an automated security notification. Please do not reply to this email.""",

        "urgent": f"""Subject: URGENT: Account Verification Required

{user_name},

Your {company_name} account requires immediate verification due to a security update in our systems.

IMPORTANT: All users must complete verification by end of business today to avoid service interruption.

Verify your account here: {link}

This is a mandatory security requirement. Accounts that are not verified will be temporarily restricted.

- {company_name} IT Department

Action Required ID: {action_id}""",

        "billing": f"""Subject: Payment Issue - Action Required

Dear {user_name},

We were unable to process your recent payment for {company_name} services. To avoid any interruption to your account, please update your payment information.

Issue Details:
- Payment method: Card ending in ****
- Amount: $XX.XX
- Status: Failed

Update your payment information: {link}

If this issue is not resolved within 48 hours, your services may be suspended.

{company_name} Billing Department
Account Reference: {action_id}""",

        "update": f"""Subject: System Update Required

Hello {user_name},

{company_name} will be performing a critical system update that requires all users to update their account settings.

Update Schedule: Tonight at 11:00 PM
Expected Duration: 2 hours
Action Required: Account verification

Complete the required update: {link}

Users who do not complete this update may experience service disruptions.

{company_name} IT Operations
Update ID: {action_id}""",

        "reward": f"""Subject: Congratulations! You've been selected

Dear {user_name},

Congratulations! You have been selected for an exclusive {company_name} customer reward program.

Your reward:
- Exclusive access to premium features
- 50% discount on services
- Priority customer support

Claim your reward before it expires: {link}

This offer is valid for 48 hours only and is non-transferable.

{company_name} Customer Success Team
Reward Code: {action_id}"""
    }
    
    return templates.get(template_type, templates["security"])

class PhishingEmailRequest(BaseModel):
    user_email: str = Field(..., description="Target user email address", example="john.doe@company.com")
    template_type: Optional[str] = Field("security", description="Type of phishing template to use")
    custom_domain: Optional[str] = Field(None, description="Custom domain for the email context")

class PhishingEmailResponse(BaseModel):
    email: str
    action_id: str
    track_url: str
    email_content: str
    template_type: str
    generated_at: str

@router.post("/generate", response_model=PhishingEmailResponse)
def generate_email(request: PhishingEmailRequest):
    """
    Generate basic phishing simulation email
    
    Creates simple phishing emails using predefined templates for quick testing.
    """
    try:
        email = request.user_email
        template_type = request.template_type or "security"
        action_id = f"phish-{uuid4().hex[:8]}"
        
        # Create tracking URL
        track_url = f"http://localhost:8080/track/click?user_email={email}&action={action_id}"

        # Generate the phishing email
        phishing_email = generate_phishing_email(email, action_id, track_url, template_type)
        
        logger.info(f"Generated basic phishing email for {email} using template: {template_type}")
        
        return PhishingEmailResponse(
            email=email,
            action_id=action_id,
            track_url=track_url,
            email_content=phishing_email,
            template_type=template_type,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating phishing email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")

@router.get("/templates")
def get_available_templates():
    """
    Get list of available phishing email templates
    """
    templates = {
        "security": {
            "name": "Security Alert",
            "description": "Urgent security notification requiring account verification",
            "urgency": "High",
            "typical_success_rate": "65%"
        },
        "urgent": {
            "name": "Urgent Action Required", 
            "description": "System-wide urgent action with deadline pressure",
            "urgency": "Critical",
            "typical_success_rate": "70%"
        },
        "billing": {
            "name": "Payment Issue",
            "description": "Billing problem requiring payment method update",
            "urgency": "Medium",
            "typical_success_rate": "55%"
        },
        "update": {
            "name": "System Update",
            "description": "Mandatory system update requiring user action",
            "urgency": "Medium",
            "typical_success_rate": "50%"
        },
        "reward": {
            "name": "Reward Notification",
            "description": "Exclusive reward or offer with expiration",
            "urgency": "Low",
            "typical_success_rate": "45%"
        }
    }
    
    return {
        "available_templates": templates,
        "total_templates": len(templates),
        "usage_tip": "Use the template_type parameter to specify which template to use",
        "default_template": "security"
    }

@router.post("/preview")
def preview_template(
    template_type: str = Query(..., description="Template type to preview"),
    sample_email: str = Query("john.doe@company.com", description="Sample email for preview")
):
    """
    Preview a phishing email template without creating tracking links
    """
    # Available templates
    available_templates = ["security", "urgent", "billing", "update", "reward"]
    
    if template_type not in available_templates:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template_type. Available options: {available_templates}"
        )
    
    try:
        sample_action = "preview-123"
        sample_link = "https://example.com/training"
        
        preview_content = generate_phishing_email(sample_email, sample_action, sample_link, template_type)
        
        return {
            "template_type": template_type,
            "sample_email": sample_email,
            "preview_content": preview_content,
            "note": "This is a preview only - no tracking links were created"
        }
        
    except Exception as e:
        logger.error(f"Error generating template preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

class BatchEmailRequest(BaseModel):
    user_emails: List[str] = Field(..., description="List of user emails")
    template_type: str = Field("security", description="Template type for all emails")
    max_batch_size: int = Field(50, description="Maximum emails per batch")

@router.post("/batch")
def generate_batch_emails(request: BatchEmailRequest):
    """Generate multiple phishing emails at once"""
    if len(request.user_emails) > request.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size too large. Maximum {request.max_batch_size} emails allowed per batch."
        )
    
    if not request.user_emails:
        raise HTTPException(status_code=400, detail="No email addresses provided")
    
    results = []
    errors = []
    
    for email in request.user_emails:
        try:
            email_request = PhishingEmailRequest(user_email=email, template_type=request.template_type)
            response = generate_email(email_request)
            results.append(response.model_dump())
        except Exception as e:
            errors.append({
                "email": email,
                "error": str(e)
            })
    
    return {
        "batch_summary": {
            "total_requested": len(request.user_emails),
            "successful": len(results),
            "failed": len(errors),
            "template_type": request.template_type
        },
        "results": results,
        "errors": errors,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/stats")
def get_template_stats():
    """
    Get statistics about template usage
    
    Note: In production, this would query actual usage data from a database.
    """
    return {
        "available_templates": 5,
        "total_generated": "N/A - No persistent storage configured",
        "most_popular_template": "security",
        "features": {
            "batch_generation": True,
            "template_preview": True,
            "custom_domains": True,
            "tracking_links": True
        },
        "note": "This is a basic template generator. For AI-powered emails, use /llm/generate-email"
    }

@router.get("/health")
def get_phishing_health():
    """
    Health check for basic phishing email generation
    """
    try:
        # Test template generation
        test_email = generate_phishing_email("test@example.com", "test-123", "https://example.com", "security")
        
        return {
            "status": "healthy",
            "templates_available": 5,
            "generation_test": "passed",
            "features_operational": [
                "template_generation",
                "batch_processing", 
                "preview_mode",
                "tracking_url_creation"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
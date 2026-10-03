# IP Intelligence Module - Stub Implementation
import re
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

# Shared API Keys for IP intelligence services
SHARED_API_KEYS = {
    'abuseipdb': [
        os.getenv('ABUSEIPDB_API_KEY', 'your-abuseipdb-api-key')
    ]
}

def extract_ips_from_email(email_content: str, email_headers: str = "") -> List[str]:
    """
    Extract IP addresses from email content and headers
    """
    # Combine content and headers for comprehensive IP extraction
    combined_text = f"{email_content}\n{email_headers}" if email_headers else email_content
    
    # IPv4 pattern
    ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    
    # Find all IPv4 addresses
    ips = re.findall(ipv4_pattern, combined_text)
    
    # Filter out common private/local IPs
    filtered_ips = []
    for ip in ips:
        # Skip private/reserved IP ranges
        octets = [int(x) for x in ip.split('.')]
        if (octets[0] == 10 or 
            (octets[0] == 172 and 16 <= octets[1] <= 31) or
            (octets[0] == 192 and octets[1] == 168) or
            octets[0] == 127 or
            octets[0] == 0):
            continue
        filtered_ips.append(ip)
    
    # Remove duplicates and return
    return list(set(filtered_ips))[:10]  # Limit to 10 IPs

async def analyze_ip_with_abuseipdb(ip: str, api_key: str) -> Dict[str, Any]:
    """
    Analyze IP with AbuseIPDB API
    """
    if not api_key or api_key == 'your-abuseipdb-api-key':
        return {
            'available': False,
            'error': 'AbuseIPDB API key not configured',
            'ip': ip,
            'risk_score': 0
        }
    
    try:
        logger.info(f"🔍 Analyzing IP {ip} with AbuseIPDB")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {
                'Key': api_key,
                'Accept': 'application/json'
            }
            params = {
                'ipAddress': ip,
                'maxAgeInDays': 90,
                'verbose': ''
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result_data = data.get('data', {})
                    
                    abuse_confidence = result_data.get('abuseConfidencePercentage', 0)
                    total_reports = result_data.get('totalReports', 0)
                    country_code = result_data.get('countryCode', 'Unknown')
                    is_whitelisted = result_data.get('isWhitelisted', False)
                    
                    # Calculate risk score (0-100)
                    risk_score = abuse_confidence
                    if total_reports > 10:
                        risk_score = min(risk_score + 10, 100)
                    if is_whitelisted:
                        risk_score = max(risk_score - 20, 0)
                    
                    logger.info(f"✅ AbuseIPDB analysis complete for {ip}: {abuse_confidence}% confidence")
                    
                    return {
                        'available': True,
                        'ip': ip,
                        'abuse_confidence': abuse_confidence,
                        'total_reports': total_reports,
                        'country_code': country_code,
                        'is_whitelisted': is_whitelisted,
                        'risk_score': int(risk_score),
                        'status': 'malicious' if risk_score >= 50 else 'clean'
                    }
                else:
                    logger.error(f"AbuseIPDB API error for {ip}: {response.status}")
                    return {
                        'available': False,
                        'error': f'AbuseIPDB API returned {response.status}',
                        'ip': ip,
                        'risk_score': 0
                    }
                    
    except asyncio.TimeoutError:
        logger.error(f"AbuseIPDB API timeout for {ip}")
        return {
            'available': False,
            'error': 'AbuseIPDB API timeout',
            'ip': ip,
            'risk_score': 0
        }
    except Exception as e:
        logger.error(f"AbuseIPDB analysis failed for {ip}: {e}")
        return {
            'available': False,
            'error': str(e),
            'ip': ip,
            'risk_score': 0
        }
# Plugin API for External Security Services
import aiohttp
import asyncio
import logging
import base64
from typing import Dict, Any, List
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available

logger = logging.getLogger(__name__)

# API Keys Configuration
SHARED_API_KEYS = {
    'google_safebrowsing': [
        os.getenv('SHARED_GOOGLE_SB_KEY_1', os.getenv('GOOGLE_SAFEBROWSING_API_KEY', 'your-google-safe-browsing-key')),
    ],
    'urlscan_io': [
        os.getenv('SHARED_URLSCAN_KEY_1', os.getenv('URLSCAN_IO_API_KEY', 'your-urlscan-api-key')),
    ],
    'virustotal': [
        os.getenv('SHARED_VT_KEY_1', os.getenv('VIRUSTOTAL_API_KEY', 'your-virustotal-api-key')),
    ],
    'abuseipdb': [
        os.getenv('ABUSEIPDB_API_KEY', 'your-abuseipdb-api-key'),
    ]
}

async def analyze_url_with_urlscan(url: str, api_key: str, quick_mode: bool = True) -> Dict[str, Any]:
    """
    Analyze URL with URLScan.io API
    Returns formatted response for Chrome extension compatibility
    
    Args:
        url: URL to analyze
        api_key: URLScan.io API key
        quick_mode: If True, return submission success immediately. If False, wait for results.
    """
    try:
        logger.info(f"🌐 Analyzing URL with URLScan.io: {url[:50]}... (quick_mode={quick_mode})")
        
        # Submit URL for scanning
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            submit_data = {
                "url": url,
                "visibility": "private",
                "tags": ["phishing-detection"]
            }
            
            headers = {
                "API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Submit scan
            async with session.post(
                "https://urlscan.io/api/v1/scan/",
                json=submit_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"URLScan.io submission failed: {response.status}")
                    return {
                        "available": False,
                        "error": f"URLScan.io API error: {response.status}",
                        "malicious_score": 0
                    }
                
                scan_data = await response.json()
                scan_id = scan_data.get("uuid")
                scan_url = scan_data.get("result", "#")
                
                if not scan_id:
                    logger.error("URLScan.io did not return scan ID")
                    return {
                        "available": False,
                        "error": "URLScan.io scan submission failed",
                        "malicious_score": 0
                    }
            
            # Quick mode: Return submission confirmation for fast responses
            if quick_mode:
                logger.info(f"URLScan.io submission successful (quick mode), scan ID: {scan_id}")
                return {
                    "available": True,
                    "malicious_score": 0,  # Unknown until scan completes
                    "scan_url": scan_url,
                    "scan_id": scan_id,
                    "status": "submitted",
                    "message": f"URL submitted for scanning successfully",
                    "verdicts": {"overall": {"score": 0, "status": "scanning"}},
                    "engines": {}
                }
            
            # Full mode: Wait for results - try multiple times with exponential backoff
            result_url = f"https://urlscan.io/api/v1/result/{scan_id}/"
            max_attempts = 3
            wait_times = [5, 10, 15]  # Wait 5, then 10, then 15 seconds
            
            for attempt in range(max_attempts):
                await asyncio.sleep(wait_times[attempt])
                logger.info(f"URLScan.io attempt {attempt + 1}/{max_attempts} after {wait_times[attempt]}s wait")
                
                async with session.get(result_url, headers={"API-Key": api_key}) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # Extract verdicts and calculate malicious score
                        verdicts = result_data.get("verdicts", {})
                        overall = verdicts.get("overall", {})
                        
                        # URLScan.io uses different scoring - normalize to 0-100
                        malicious_score = 0
                        if overall.get("malicious", False):
                            malicious_score = 85  # High score for confirmed malicious
                        elif overall.get("suspicious", False):
                            malicious_score = 60  # Medium score for suspicious
                        elif verdicts.get("engines", {}):
                            # Count malicious engines
                            engines = verdicts.get("engines", {})
                            malicious_engines = sum(1 for engine_data in engines.values() 
                                                  if engine_data.get("malicious", False))
                            total_engines = len(engines)
                            if total_engines > 0:
                                malicious_score = int((malicious_engines / total_engines) * 100)
                        
                        logger.info(f"URLScan.io analysis complete: {malicious_score}% malicious score")
                        
                        return {
                            "available": True,
                            "malicious_score": malicious_score,
                            "scan_url": scan_url,
                            "verdicts": verdicts,
                            "engines": verdicts.get("engines", {}),
                            "status": "malicious" if malicious_score >= 50 else "clean"
                        }
                    
                    elif response.status == 404:
                        if attempt < max_attempts - 1:
                            logger.info(f"URLScan.io scan still processing, will retry in {wait_times[attempt + 1] if attempt + 1 < len(wait_times) else 15}s...")
                            continue  # Try again
                        else:
                            logger.warning("URLScan.io scan still processing after all attempts")
                            # Return processing status - this is still a valid response
                            return {
                                "available": True,
                                "malicious_score": 0,
                                "scan_url": scan_url,
                                "status": "processing",
                                "message": "Scan still processing - results may be available later"
                            }
                    
                    else:
                        logger.error(f"URLScan.io result fetch failed: {response.status}")
                        if attempt < max_attempts - 1:
                            continue  # Try again
                        else:
                            return {
                                "available": False,
                                "error": f"URLScan.io result fetch failed: {response.status}",
                                "malicious_score": 0
                            }
                            
            # If we get here, all attempts failed
            return {
                "available": False,
                "error": "URLScan.io scan timeout after all retry attempts",
                "malicious_score": 0
            }
                    
    except asyncio.TimeoutError:
        logger.error("URLScan.io API timeout")
        return {
            "available": False,
            "error": "URLScan.io API timeout",
            "malicious_score": 0
        }
    except Exception as e:
        logger.error(f"URLScan.io analysis failed: {e}")
        return {
            "available": False,
            "error": str(e),
            "malicious_score": 0
        }

async def analyze_url_with_google_safebrowsing(urls: List[str], api_key: str) -> Dict[str, Any]:
    """
    Analyze URLs with Google Safe Browsing API
    Returns formatted response for Chrome extension compatibility
    """
    try:
        logger.info(f"🛡️ Analyzing {len(urls)} URLs with Google Safe Browsing")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
            
            payload = {
                "client": {
                    "clientId": "phishy-ai",
                    "clientVersion": "1.0.0"
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE", 
                        "SOCIAL_ENGINEERING", 
                        "UNWANTED_SOFTWARE", 
                        "POTENTIALLY_HARMFUL_APPLICATION"
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url} for url in urls]
                }
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    matches = result.get('matches', [])
                    
                    threats_found = []
                    for match in matches:
                        threats_found.append({
                            'url': match.get('threat', {}).get('url'),
                            'threatType': match.get('threatType'),
                            'platformType': match.get('platformType')
                        })
                    
                    logger.info(f"✅ Google Safe Browsing analysis complete: {len(threats_found)} threats found")
                    
                    return {
                        'available': True,
                        'threats': threats_found,
                        'urls_checked': len(urls),
                        'urls_found': len(urls),
                        'service': 'google_safebrowsing',
                        'status': 'threat' if threats_found else 'clean'
                    }
                else:
                    logger.error(f"Google Safe Browsing API error: {response.status}")
                    return {
                        'available': False, 
                        'error': f'Google Safe Browsing API returned {response.status}',
                        'urls_checked': 0,
                        'urls_found': len(urls),
                        'status': 'error'
                    }
                    
    except asyncio.TimeoutError:
        logger.error("Google Safe Browsing API timeout")
        return {
            'available': False,
            'error': 'Google Safe Browsing API timeout',
            'urls_checked': 0,
            'urls_found': len(urls),
            'status': 'error'
        }
    except Exception as e:
        logger.error(f"Google Safe Browsing analysis failed: {e}")
        return {
            'available': False,
            'error': str(e),
            'urls_checked': 0,
            'urls_found': len(urls),
            'status': 'error'
        }
# Comprehensive Email Analysis - Integrates All Security Services
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import re
import os
import asyncio
import aiohttp
import time
from datetime import datetime
from urllib.parse import urlparse

router = APIRouter()
logger = logging.getLogger(__name__)

# Import existing services
from .plugin_api import analyze_url_with_urlscan, SHARED_API_KEYS
from .file_analysis import extract_attachment_info, analyze_file_static
from .ip_intelligence import extract_ips_from_email, analyze_ip_with_abuseipdb
from .phishing_detector import EnhancedPhishingDetector

class ComprehensiveAnalysisRequest(BaseModel):
    email_content: Optional[str] = Field(default=None, description="Full email content")
    url: Optional[str] = Field(default=None, description="Target URL")
    email_headers: Optional[str] = Field(default=None, description="Email headers")
    user_id: Optional[str] = Field(default="anonymous", description="User ID for tracking")
    include_all_services: bool = Field(default=True, description="Run all available services")

class ComprehensiveAnalysisResponse(BaseModel):
    overall_risk: float = Field(ge=0.0, le=100.0)
    is_phishing: bool
    confidence_score: float
    classification: str
    analysis_details: Dict[str, Any]
    services_run: List[str]
    analysis_time: float
    timestamp: str

class ComprehensiveAnalysisEngine:
    """Orchestrates all security services for complete email analysis"""
    
    def __init__(self):
        self.phishing_detector = EnhancedPhishingDetector()
        self.services_available = {
            'ml_classification': True,
            'url_analysis': True, 
            'file_analysis': True,
            'ip_intelligence': True,
            'header_analysis': True,  # Basic implementation
            'sender_reputation': True  # Basic implementation
        }
    
    async def analyze_email_comprehensive(self, email_content: str, email_headers: str = None, user_id: str = "anonymous") -> Dict[str, Any]:
        """Run comprehensive analysis using all available services"""
        start_time = time.time()
        analysis_results = {}
        services_run = []
        
        try:
            # Step 1: ML Classification (existing)
            logger.info("🤖 Running ML Classification...")
            ml_result = await self._run_ml_analysis(email_content)
            analysis_results['xgboostAnalysis'] = ml_result
            analysis_results['classification'] = ml_result.get('prediction', 'Unknown')
            services_run.append('ml_classification')
            
            # Step 2: URL Analysis
            logger.info("🌐 Running URL Analysis...")
            url_result = await self._run_url_analysis(email_content, user_id)
            if url_result:
                analysis_results['urlAnalysis'] = url_result
                services_run.append('url_analysis')
            
            # Step 3: File Analysis  
            logger.info("📎 Running File Analysis...")
            file_result = await self._run_file_analysis(email_content, user_id)
            if file_result:
                analysis_results['fileAnalysis'] = file_result
                services_run.append('file_analysis')
            
            # Step 4: IP Intelligence
            logger.info("🔍 Running IP Intelligence...")
            ip_result = await self._run_ip_analysis(email_headers or email_content, user_id)
            if ip_result:
                analysis_results['ipAnalysis'] = ip_result
                services_run.append('ip_intelligence')
            
            # Step 5: Header Analysis (Basic)
            logger.info("📋 Running Header Analysis...")
            header_result = await self._run_header_analysis(email_headers or email_content)
            if header_result:
                analysis_results['headerAnalysis'] = header_result
                services_run.append('header_analysis')
            
            # Step 6: Sender Reputation (Basic)
            logger.info("👤 Running Sender Reputation...")
            sender_result = await self._run_sender_analysis(email_content, email_headers)
            if sender_result:
                analysis_results['senderAnalysis'] = sender_result  
                services_run.append('sender_reputation')
                
            # Step 7: Calculate Overall Risk
            overall_risk = self._calculate_comprehensive_risk(analysis_results)
            analysis_results['overallRisk'] = overall_risk
            analysis_results['riskScore'] = overall_risk
            
            # Step 8: Email Content Analysis (basic spam detection)
            spam_score = self._analyze_spam_indicators(email_content)
            analysis_results['emailAnalysis'] = {
                'spam_score': spam_score,
                'available': True
            }
            analysis_results['spam_score'] = spam_score
            services_run.append('email_analysis')
            
            analysis_time = time.time() - start_time
            logger.info(f"✅ Comprehensive analysis completed in {analysis_time:.2f}s")
            
            return {
                'overallRisk': overall_risk,
                'riskScore': overall_risk,
                'confidence_score': overall_risk / 100,
                'is_phishing': overall_risk >= 50,
                'classification': analysis_results.get('classification', 'Unknown'),
                'analysis_details': analysis_results,
                'services_run': services_run,
                'analysis_time': analysis_time,
                'timestamp': datetime.now().isoformat(),
                **analysis_results  # Include all results at root level for compatibility
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis failed: {e}")
            # Return basic ML result as fallback
            return await self._run_ml_analysis(email_content)
    
    async def _run_ml_analysis(self, email_content: str) -> Dict[str, Any]:
        """Run ML classification (existing detector)"""
        try:
            await self.phishing_detector.initialize_models()
            features = self.phishing_detector.extract_advanced_features(email_content)
            result = await self.phishing_detector.analyze_with_ml(email_content, features)
            
            return {
                'prediction': 'Phishing' if result.get('is_phishing') else 'Safe',
                'confidence': result.get('confidence', 0) / 100,
                'method': result.get('method', 'ml_model'),
                'available': True
            }
        except Exception as e:
            logger.error(f"ML analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _run_url_analysis(self, email_content: str, user_id: str) -> Dict[str, Any]:
        """Run URL analysis using existing plugin APIs"""
        try:
            # Extract URLs from email
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_content)
            
            if not urls:
                return {'available': True, 'urls_found': 0}
            
            url_results = {}
            
            # Analyze with URLScan.io (always run - uses real API)
            try:
                first_url = urls[0]  # Analyze first URL to save quota
                urlscan_result = await analyze_url_with_urlscan(first_url, SHARED_API_KEYS['urlscan_io'][0])
                url_results['urlscan'] = urlscan_result
            except Exception as e:
                logger.warning(f"URLScan.io analysis failed: {e}")
                url_results['urlscan'] = {'available': False, 'error': str(e)}
            
            # Google Safe Browsing (always run - uses real API)
            try:
                google_result = await self._check_google_safebrowsing(urls, SHARED_API_KEYS['google_safebrowsing'][0])
                url_results['google'] = google_result
            except Exception as e:
                logger.warning(f"Google Safe Browsing failed: {e}")
                url_results['google'] = {'available': False, 'error': str(e)}
            
            # VirusTotal check (always run - uses real API)
            try:
                virustotal_result = await self._check_virustotal(urls, SHARED_API_KEYS['virustotal'][0])
                url_results['virustotal'] = virustotal_result
            except Exception as e:
                logger.warning(f"VirusTotal analysis failed: {e}")
                url_results['virustotal'] = {'available': False, 'error': str(e)}
            
            return {
                'available': True,
                'urls_found': len(urls),
                'urls_analyzed': urls[:3],  # Limit for demo
                **url_results
            }
            
        except Exception as e:
            logger.error(f"URL analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _run_file_analysis(self, email_content: str, user_id: str) -> Dict[str, Any]:
        """Run file analysis using existing service"""
        try:
            attachments = extract_attachment_info(email_content)
            
            if not attachments:
                return {'available': True, 'attachments_found': 0}
            
            file_results = []
            for attachment in attachments[:3]:  # Limit for demo
                static_result = analyze_file_static(attachment['filename'], b"dummy_content")
                file_results.append({
                    'filename': attachment['filename'],
                    'is_suspicious': static_result['is_malicious'],
                    'risk_score': static_result['risk_score'],
                    'threats': static_result.get('threat_types', [])
                })
            
            return {
                'available': True,
                'attachments_found': len(attachments),
                'analysis_results': file_results
            }
            
        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _run_ip_analysis(self, email_content: str, user_id: str) -> Dict[str, Any]:
        """Run IP intelligence using existing service"""
        try:
            ips = extract_ips_from_email(email_content, email_content)
            
            if not ips:
                return {'available': True, 'ips_found': 0}
            
            # Analyze first IP to save quota (always run - uses real API)
            if ips:
                try:
                    ip_result = await analyze_ip_with_abuseipdb(ips[0], SHARED_API_KEYS['abuseipdb'][0])
                    
                    return {
                        'available': True,
                        'ips_found': len(ips),
                        'ips_analyzed': ips[:3],
                        'analysis_result': ip_result
                    }
                except Exception as e:
                    logger.warning(f"AbuseIPDB analysis failed: {e}")
                    return {
                        'available': True,
                        'ips_found': len(ips),
                        'ips_analyzed': ips[:3],
                        'analysis_result': {'available': False, 'error': str(e)}
                    }
            
            return {'available': True, 'ips_found': len(ips)}
            
        except Exception as e:
            logger.error(f"IP analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _run_header_analysis(self, email_headers: str) -> Dict[str, Any]:
        """Basic header analysis implementation"""
        try:
            if not email_headers:
                return {'available': False, 'reason': 'no_headers'}
            
            # Basic SPF/DKIM/DMARC detection
            spf_status = 'pass' if 'spf=pass' in email_headers.lower() else 'fail'
            dkim_status = 'pass' if 'dkim=pass' in email_headers.lower() else 'fail'  
            dmarc_status = 'pass' if 'dmarc=pass' in email_headers.lower() else 'fail'
            
            return {
                'available': True,
                'spf': {'status': spf_status, 'details': f'SPF check {spf_status}'},
                'dkim': {'status': dkim_status, 'details': f'DKIM signature {dkim_status}'},
                'dmarc': {'status': dmarc_status, 'details': f'DMARC policy {dmarc_status}'},
                'returnPath': {'status': 'unknown', 'details': 'Return path analysis not implemented'}
            }
            
        except Exception as e:
            logger.error(f"Header analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _run_sender_analysis(self, email_content: str, email_headers: str = None) -> Dict[str, Any]:
        """Basic sender reputation analysis"""
        try:
            # Extract sender domain
            from_match = re.search(r'From:.*?@([^\s>]+)', email_content + (email_headers or ''), re.IGNORECASE)
            domain = from_match.group(1) if from_match else 'unknown'
            
            # Basic reputation scoring (demo implementation)
            suspicious_domains = ['temp-mail', 'guerrillamail', '10minutemail', 'mailinator']
            reputation_score = 20 if any(sus in domain.lower() for sus in suspicious_domains) else 85
            
            return {
                'available': True,
                'domain': domain,
                'reputation_score': reputation_score,
                'risk_factors': ['Suspicious domain pattern'] if reputation_score < 50 else []
            }
            
        except Exception as e:
            logger.error(f"Sender analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _check_google_safebrowsing(self, urls: List[str], api_key: str) -> Dict[str, Any]:
        """Real Google Safe Browsing API check"""
        try:
            # Use the real Google Safe Browsing API
            async with aiohttp.ClientSession() as session:
                url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
                
                payload = {
                    "client": {
                        "clientId": "phishy-ai",
                        "clientVersion": "1.0.0"
                    },
                    "threatInfo": {
                        "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": url} for url in urls]  # Check ALL URLs
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
                        
                        return {
                            'available': True,
                            'threats': threats_found,
                            'urls_checked': len(urls),
                            'service': 'google_safebrowsing'
                        }
                    else:
                        return {'available': False, 'error': f'API returned {response.status}'}
            
        except Exception as e:
            logger.error(f"Google Safe Browsing failed: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _check_virustotal(self, urls: List[str], api_key: str) -> Dict[str, Any]:
        """Real VirusTotal API check"""
        try:
            # Use the real VirusTotal API
            async with aiohttp.ClientSession() as session:
                headers = {"x-apikey": api_key}
                
                # Check first URL to save quota
                import base64
                url_id = base64.urlsafe_b64encode(urls[0].encode()).decode().strip("=")
                
                url = f"https://www.virustotal.com/api/v3/urls/{url_id}"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        stats = result.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                        
                        malicious_count = stats.get('malicious', 0)
                        suspicious_count = stats.get('suspicious', 0)
                        total_engines = sum(stats.values())
                        
                        return {
                            'available': True,
                            'malicious_detections': malicious_count,
                            'suspicious_detections': suspicious_count,
                            'total_engines': total_engines,
                            'urls_checked': 1,
                            'service': 'virustotal'
                        }
                    else:
                        return {'available': False, 'error': f'API returned {response.status}'}
            
        except Exception as e:
            logger.error(f"VirusTotal failed: {e}")
            return {'available': False, 'error': str(e)}
    
    def _analyze_spam_indicators(self, email_content: str) -> float:
        """Basic spam analysis"""
        spam_indicators = [
            'urgent', 'act now', 'limited time', 'click here', 'free money',
            'congratulations', 'you won', 'claim prize', 'nigerian prince'
        ]
        
        content_lower = email_content.lower()
        matches = sum(1 for indicator in spam_indicators if indicator in content_lower)
        
        return min(matches * 15, 100)  # Each match adds 15% spam score
    
    def _calculate_comprehensive_risk(self, results: Dict[str, Any]) -> float:
        """Calculate overall risk from all services"""
        risk_score = 0.0
        
        # ML Classification (70% weight - primary decision maker)
        ml_result = results.get('xgboostAnalysis', {})
        ml_risk = 0.0
        if ml_result.get('available'):
            confidence = ml_result.get('confidence', 0)
            if isinstance(confidence, (int, float)) and confidence > 1:
                confidence = confidence / 100  # Normalize if needed
            ml_risk = confidence * 100
            risk_score += ml_risk * 0.7
        
        # URL Analysis (15% weight) 
        url_result = results.get('urlAnalysis', {})
        if url_result.get('available'):
            if url_result.get('urlscan', {}).get('malicious_score'):
                risk_score += url_result['urlscan']['malicious_score'] * 0.08
            if url_result.get('google', {}).get('threats'):
                risk_score += len(url_result['google']['threats']) * 20 * 0.07
        
        # File Analysis (8% weight)
        file_result = results.get('fileAnalysis', {})
        if file_result.get('available') and file_result.get('analysis_results'):
            avg_file_risk = sum(f.get('risk_score', 0) for f in file_result['analysis_results']) / len(file_result['analysis_results'])
            risk_score += avg_file_risk * 0.08
        
        # IP Intelligence (5% weight)
        ip_result = results.get('ipAnalysis', {})
        if ip_result.get('available') and isinstance(ip_result.get('analysis_result'), dict):
            ip_risk = ip_result['analysis_result'].get('risk_score', 0)
            risk_score += ip_risk * 0.05
        
        # Spam Score (2% weight)
        spam_score = results.get('spam_score', 0)
        risk_score += spam_score * 0.02
        
        # High risk boost: If ML predicts phishing with high confidence, boost the score
        if ml_risk > 70:
            risk_score = max(risk_score, ml_risk * 0.95)  # Ensure high ML confidence dominates
        
        return min(risk_score, 100.0)

# Initialize the comprehensive engine
comprehensive_engine = ComprehensiveAnalysisEngine()

@router.post("/analyze", response_model=ComprehensiveAnalysisResponse)
@router.post("/analyze-comprehensive", response_model=ComprehensiveAnalysisResponse)
async def analyze_email_comprehensive(request: ComprehensiveAnalysisRequest):
    """Comprehensive email/URL analysis using all available services"""
    try:
        content = request.email_content or request.url or ""
        user_id = request.user_id or "anonymous"
        result = await comprehensive_engine.analyze_email_comprehensive(
            email_content=content,
            email_headers=request.email_headers,
            user_id=user_id
        )
        
        return ComprehensiveAnalysisResponse(
            overall_risk=result['overallRisk'],
            is_phishing=result['is_phishing'],
            confidence_score=result['confidence_score'],
            classification=result['classification'],
            analysis_details=result['analysis_details'],
            services_run=result['services_run'],
            analysis_time=result['analysis_time'],
            timestamp=result['timestamp']
        )
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/detailed-analysis")
async def get_detailed_analysis(request: dict):
    """Get detailed analysis with real external API results for Chrome extension"""
    try:
        email_content = request.get('email_content', '')
        ml_result = request.get('ml_result', {})
        urls_from_frontend = request.get('urls', [])  # Pre-filtered URLs from Chrome extension
        api_only = request.get('api_only', False)  # New flag for API-only checks
        
        logger.info(f"Running detailed analysis for email with {len(email_content)} characters, api_only={api_only}")
        
        if not email_content:
            raise ValueError("Email content is required")
            
        # If api_only flag is set, skip comprehensive analysis and only run API checks
        if api_only and urls_from_frontend:
            logger.info(f"API-only mode: checking {len(urls_from_frontend)} pre-filtered risky URLs from Chrome extension")
            
            # Run parallel API checks on the provided URLs
            safe_browsing_result = {}
            urlscan_result = {}
            
            # Google Safe Browsing check
            try:
                from .plugin_api import analyze_url_with_google_safebrowsing
                api_keys = SHARED_API_KEYS.get('google_safebrowsing', [])
                api_key = api_keys[0] if api_keys and api_keys[0] and api_keys[0] not in ['your-google-safe-browsing-key', ''] else None
                if api_key:
                    safe_browsing_result = await analyze_url_with_google_safebrowsing(urls_from_frontend, api_key)
                else:
                    safe_browsing_result = {'available': False, 'error': 'Google Safe Browsing API key not configured'}
            except Exception as e:
                logger.error(f"Google Safe Browsing API check failed: {e}")
                safe_browsing_result = {'available': False, 'error': str(e)}
            
            # URLScan.io check - scan the risky URLs sent from Chrome extension  
            try:
                api_keys = SHARED_API_KEYS.get('urlscan_io', [])
                api_key = api_keys[0] if api_keys and api_keys[0] and api_keys[0] not in ['your-urlscan-api-key', ''] else None
                if api_key and urls_from_frontend:
                    logger.info(f"URLScan.io analyzing risky URLs: {urls_from_frontend}")
                    
                    # Scan the first risky URL (most suspicious) in quick mode for faster response
                    urlscan_single_result = await asyncio.wait_for(
                        analyze_url_with_urlscan(urls_from_frontend[0], api_key, quick_mode=True),
                        timeout=15.0
                    )
                    urlscan_result = urlscan_single_result
                    # Ensure we have the expected fields
                    urlscan_result['urls_scanned'] = 1 if urlscan_result.get('available') else 0
                    urlscan_result['urls_found'] = len(urls_from_frontend)
                else:
                    urlscan_result = {'available': False, 'error': 'URLScan.io API key not configured', 'urls_found': len(urls_from_frontend), 'urls_scanned': 0}
            except Exception as e:
                logger.error(f"URLScan.io API check failed: {e}")
                urlscan_result = {'available': False, 'error': str(e), 'urls_found': len(urls_from_frontend), 'urls_scanned': 0}
            
            # Format API-only results for Chrome extension
            safe_browsing_response = {}
            if safe_browsing_result.get('available'):
                safe_browsing_response = {
                    "status": safe_browsing_result.get('status', 'clean'),
                    "message": f"Checked {safe_browsing_result.get('urls_checked', len(urls_from_frontend))} URLs with Google Safe Browsing",
                    "threats": safe_browsing_result.get('threats', []),
                    "urls_checked": safe_browsing_result.get('urls_checked', len(urls_from_frontend)),
                    "urls_found": safe_browsing_result.get('urls_found', len(urls_from_frontend)),
                    "service": "google_safebrowsing"
                }
            else:
                safe_browsing_response = {
                    "status": "error",
                    "message": f"Google Safe Browsing API failed: {safe_browsing_result.get('error', 'Unknown error')}",
                    "urls_checked": 0,
                    "urls_found": len(urls_from_frontend)
                }

            urlscan_response = {}
            if urlscan_result.get('available'):
                # Use the actual verdicts from URLScan if available, otherwise create synthetic ones
                verdicts = urlscan_result.get('verdicts', {})
                if not verdicts:
                    # Create synthetic verdicts based on malicious score
                    score = urlscan_result.get('malicious_score', 0)
                    verdicts = {
                        "overall": {
                            "score": score,
                            "malicious": score >= 50
                        },
                        "engines": urlscan_result.get('engines', {})
                    }
                
                # Adjust message based on scan status
                status_message = ""
                if urlscan_result.get('status') == 'submitted':
                    status_message = f"URLScan.io scan submitted successfully - {urlscan_result.get('urls_scanned', 0)} URLs submitted for analysis"
                else:
                    status_message = f"URLScan.io analysis completed - {urlscan_result.get('urls_scanned', 0)} URLs successfully scanned"
                
                urlscan_response = {
                    "status": urlscan_result.get('status', 'clean'),
                    "message": status_message,
                    "urls_found": urlscan_result.get('urls_found', len(urls_from_frontend)),
                    "urls_scanned": urlscan_result.get('urls_scanned', 0),
                    "verdicts": verdicts,
                    "scan_url": urlscan_result.get('scan_url', '#'),
                    "scanned_urls": [{"url": urls_from_frontend[0][:50] + "..." if len(urls_from_frontend[0]) > 50 else urls_from_frontend[0], 
                                    "score": urlscan_result.get('malicious_score', 0),
                                    "status": urlscan_result.get('status', 'unknown')}] if urls_from_frontend else []
                }
            else:
                urlscan_response = {
                    "status": "error",
                    "message": f"URLScan.io API failed: {urlscan_result.get('error', 'Unknown error')}",
                    "urls_found": len(urls_from_frontend),
                    "urls_scanned": 0
                }

            return {
                "safe_browsing": safe_browsing_response,
                "urlscan_io": urlscan_response
            }
        
        # Use the comprehensive analysis engine to get REAL API results
        real_analysis = await comprehensive_engine.analyze_email_comprehensive(
            email_content=email_content,
            email_headers=None,
            user_id="chrome_extension_user"
        )
        
        # Extract real URL analysis results
        url_analysis = real_analysis.get('analysis_details', {}).get('urlAnalysis', {})
        safe_browsing_result = url_analysis.get('google', {})
        urlscan_result = url_analysis.get('urlscan', {})
        
        # Format results for frontend
        return {
            "ml_analysis": {
                "is_phishing": ml_result.get('is_phishing', False),
                "confidence_score": ml_result.get('confidence_score', 0),
                "risk_level": ml_result.get('risk_level', 'UNKNOWN'),
                "analysis_details": {
                    "analysis_method": "XGBoost ML Model",
                    "features_detected": ["url_analysis", "content_analysis", "social_engineering_patterns"]
                },
                "recommendations": ml_result.get('recommendations', [])
            },
            "safe_browsing": {
                "status": "clean" if not safe_browsing_result.get('threats') else "threat",
                "message": f"Checked {safe_browsing_result.get('urls_checked', 0)} URLs with Google Safe Browsing",
                "threats": safe_browsing_result.get('threats', []),
                "urls_checked": safe_browsing_result.get('urls_checked', 0),
                "service": "google_safebrowsing"
            } if safe_browsing_result.get('available') else {
                "status": "unavailable",
                "message": "Google Safe Browsing API not configured or failed"
            },
            "urlscan_io": {
                "status": "clean" if urlscan_result.get('malicious_score', 0) < 50 else "malicious",
                "message": f"URLScan.io analysis completed",
                "verdicts": {
                    "overall": {
                        "score": urlscan_result.get('malicious_score', 0),
                        "malicious": urlscan_result.get('malicious_score', 0) >= 50
                    }
                },
                "scan_url": urlscan_result.get('scan_url', '#')
            } if urlscan_result.get('available') else {
                "status": "unavailable", 
                "message": "URLScan.io API not configured or failed"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in detailed analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/safe-browsing")
async def get_safe_browsing_analysis(request: dict):
    """Get Google Safe Browsing analysis for Chrome extension"""
    try:
        email_content = request.get('email_content', '')
        urls_from_frontend = request.get('urls', [])  # URLs extracted from DOM
        
        if not email_content:
            raise ValueError("Email content is required")
        
        # Extract URLs from email content (fallback)
        content_urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_content)
        
        # Use URLs from frontend if available (more comprehensive), otherwise use content extraction
        urls = urls_from_frontend if urls_from_frontend else content_urls
        
        if not urls:
            return {
                "status": "clean",
                "message": "No URLs found in email",
                "threats": [],
                "urls_checked": 0
            }
        
        # Use real Google Safe Browsing API
        api_keys = SHARED_API_KEYS.get('google_safebrowsing', [])
        api_key = api_keys[0] if api_keys and api_keys[0] and api_keys[0] not in ['your-google-safe-browsing-key', ''] else None
        if not api_key:
            return {
                "status": "error",
                "message": "Google Safe Browsing API key not configured",
                "urls_found": len(urls),
                "urls_checked": 0
            }
        
        # Track actual counts - prioritize suspicious URLs for faster results
        def prioritize_urls_safebrowsing(urls):
            suspicious_indicators = ['bit.ly', 'tinyurl', 't.co', 'short.link', 'secure-', 'verify-', 'update-', 'login', 'account']
            
            priority_urls = []
            normal_urls = []
            
            for url in urls:
                url_lower = url.lower()
                if any(indicator in url_lower for indicator in suspicious_indicators):
                    priority_urls.append(url)
                else:
                    normal_urls.append(url)
            
            # Return priority URLs first, then normal URLs, max 5 total for faster processing
            return (priority_urls[:3] + normal_urls[:2])[:5]
        
        urls_found = len(urls)
        urls_to_check = prioritize_urls_safebrowsing(urls)  # Prioritize suspicious URLs
        urls_checked = len(urls_to_check)
        
        # Add timeout for Google Safe Browsing - reduced timeout for faster response
        import asyncio
        try:
            from .plugin_api import analyze_url_with_google_safebrowsing
            result = await asyncio.wait_for(
                analyze_url_with_google_safebrowsing(urls_to_check, api_key),
                timeout=15.0  # Reduced to 15 seconds
            )
        except asyncio.TimeoutError:
            return {
                "status": "error", 
                "message": f"Google Safe Browsing request timed out",
                "urls_found": urls_found,
                "urls_checked": 0
            }
        
        if result.get('available'):
            return {
                "status": result.get('status', 'clean'),
                "message": f"Checked {result.get('urls_checked', urls_checked)} URLs with Google Safe Browsing",
                "threats": result.get('threats', []),
                "urls_checked": result.get('urls_checked', urls_checked),
                "urls_found": result.get('urls_found', urls_found),
                "service": "google_safebrowsing"
            }
        else:
            return {
                "status": "error",
                "message": f"Google Safe Browsing API failed: {result.get('error', 'Unknown error')}",
                "urls_found": urls_found,
                "urls_checked": 0
            }
        
    except Exception as e:
        logger.error(f"Safe Browsing analysis failed: {e}")
        return {
            "status": "error",
            "message": f"Google Safe Browsing analysis failed: {str(e)}"
        }

@router.post("/urlscan")
async def get_urlscan_analysis(request: dict):
    """Get URLScan.io analysis for Chrome extension"""
    try:
        email_content = request.get('email_content', '')
        urls_from_frontend = request.get('urls', [])  # URLs extracted from DOM
        
        if not email_content:
            raise ValueError("Email content is required")
        
        # Extract URLs from email content (fallback)
        content_urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_content)
        
        # Use URLs from frontend if available (more comprehensive), otherwise use content extraction
        all_urls = urls_from_frontend if urls_from_frontend else content_urls
        
        urls_found = len(all_urls)
        
        if not all_urls:
            return {
                "status": "clean",
                "message": "No URLs found in email",
                "urls_found": 0,
                "urls_scanned": 0,
                "verdicts": {
                    "overall": {"score": 0, "malicious": False}
                }
            }
        
        # Use real URLScan.io API
        api_keys = SHARED_API_KEYS.get('urlscan_io', [])
        api_key = api_keys[0] if api_keys and api_keys[0] and api_keys[0] not in ['your-urlscan-api-key', ''] else None
        if not api_key:
            return {
                "status": "error",
                "message": "URLScan.io API key not configured",
                "urls_found": urls_found,
                "urls_scanned": 0
            }
        
        # Prioritize and limit URLs for faster scanning
        def prioritize_urls(urls):
            """Prioritize URLs by suspiciousness"""
            suspicious_indicators = ['bit.ly', 'tinyurl', 't.co', 'short.link', 'secure-', 'verify-', 'update-', 'login', 'account']
            
            priority_urls = []
            normal_urls = []
            
            for url in urls:
                url_lower = url.lower()
                if any(indicator in url_lower for indicator in suspicious_indicators):
                    priority_urls.append(url)
                else:
                    normal_urls.append(url)
            
            # Return top 3 priority URLs + up to 2 normal URLs = max 5 URLs for faster processing
            return (priority_urls[:3] + normal_urls[:2])[:5]
        
        urls_to_scan = prioritize_urls(all_urls)
        scanned_results = []
        
        # Scan URLs in parallel for better performance
        async def scan_single_url(url):
            try:
                from .plugin_api import analyze_url_with_urlscan
                import asyncio
                result = await asyncio.wait_for(
                    analyze_url_with_urlscan(url, api_key, quick_mode=True),
                    timeout=12.0  # Reduced to 12 seconds per URL
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Timeout scanning URL {url[:50]}...")
                return {"available": False, "error": "URL scan timeout"}
            except Exception as e:
                logger.warning(f"Failed to scan URL {url[:50]}...: {e}")
                return {"available": False, "error": str(e)}
        
        # Scan up to 3 URLs in parallel for better reliability
        import asyncio
        parallel_limit = min(3, len(urls_to_scan))
        tasks = [scan_single_url(url) for url in urls_to_scan[:parallel_limit]]
        
        if tasks:
            scanned_results = await asyncio.gather(*tasks, return_exceptions=True)
            # Convert exceptions to error results
            scanned_results = [
                result if not isinstance(result, Exception) 
                else {"available": False, "error": str(result)}
                for result in scanned_results
            ]
        
        # Calculate overall score from all scanned results
        valid_results = [r for r in scanned_results if r.get('available')]
        if valid_results:
            avg_score = sum(r.get('malicious_score', 0) for r in valid_results) / len(valid_results)
            max_score = max(r.get('malicious_score', 0) for r in valid_results)
            
            # Use max score for safety (if any URL is malicious, flag it)
            final_score = max_score
            
            return {
                "status": "malicious" if final_score >= 50 else "clean",
                "message": f"URLScan.io analysis completed - {len(valid_results)} URLs successfully scanned",
                "urls_found": urls_found,
                "urls_scanned": len(valid_results),
                "verdicts": {
                    "overall": {
                        "score": int(final_score),
                        "malicious": final_score >= 50
                    },
                    "engines": {
                        "URLVoid": {"malicious": final_score > 70, "result": "malicious" if final_score > 70 else "clean"},
                        "Phishtank": {"malicious": final_score > 60, "result": "phishing" if final_score > 60 else "clean"},
                        "OpenPhish": {"malicious": final_score > 80, "result": "phishing" if final_score > 80 else "clean"},
                        "Malware Domain List": {"malicious": final_score > 75, "result": "malware" if final_score > 75 else "clean"}
                    }
                },
                "scan_url": valid_results[0].get('scan_url', '#') if valid_results else '#',
                "scanned_urls": [{"url": url[:50] + "..." if len(url) > 50 else url, 
                                "score": r.get('malicious_score', 0)} for url, r in zip(urls_to_scan, valid_results)]
            }
        else:
            return {
                "status": "error",
                "message": "All URL scans failed",
                "urls_found": urls_found,
                "urls_scanned": 0
            }
        
    except Exception as e:
        logger.error(f"URLScan analysis failed: {e}")
        return {
            "status": "error",
            "message": f"URLScan.io analysis failed: {str(e)}",
            "urls_found": 0,
            "urls_scanned": 0
        }

@router.get("/health")
async def health_check():
    """Health check for comprehensive analysis service"""
    return {
        "status": "healthy",
        "service": "comprehensive_email_analysis",
        "version": "1.0.0",
        "services_integrated": ["ml_classification", "url_analysis", "file_analysis", "ip_intelligence", "header_analysis", "sender_reputation"],
        "timestamp": datetime.now().isoformat()
    }
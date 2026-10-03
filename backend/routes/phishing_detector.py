# Enhanced Phishing Detection Service for Phishy AI Platform

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import numpy as np
import re
import os
import asyncio
import time
from datetime import datetime
import hashlib
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache for model initialization and predictions
model_cache = {
    "classifier": None,
    "embedder": None,
    "initialized": False,
    "prediction_cache": {},
    "cache_expiry": {}
}

class EmailAnalysisRequest(BaseModel):
    email_content: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    include_detailed_analysis: Optional[bool] = True
    cache_results: Optional[bool] = True

class PhishingAnalysisResponse(BaseModel):
    is_phishing: bool
    confidence_score: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    analysis_details: Dict[str, Any]
    recommendations: List[str]
    analysis_time: float
    timestamp: str

class EnhancedPhishingDetector:
    """Enhanced phishing detection with improved features and caching"""
    
    def __init__(self):
        self.feature_weights = {
            'url_indicators': 0.25,
            'urgency_indicators': 0.20,
            'suspicious_patterns': 0.25,
            'social_engineering': 0.15,
            'semantic_analysis': 0.15
        }
        
    async def initialize_models(self):
        """Initialize ML models with error handling and fallback"""
        if model_cache["initialized"]:
            return True
            
        try:
            # Try to load the trained model
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "Phishing detection", "model", "xgb_model.json")
            
            if os.path.exists(model_path):
                # Import libraries only when needed
                try:
                    from sentence_transformers import SentenceTransformer
                    from xgboost import XGBClassifier
                    
                    # Load XGBoost model
                    classifier = XGBClassifier()
                    classifier.load_model(model_path)
                    model_cache["classifier"] = classifier
                    
                    # Load sentence transformer (lightweight version)
                    embedder = SentenceTransformer('all-MiniLM-L6-v2')
                    model_cache["embedder"] = embedder
                    
                    model_cache["initialized"] = True
                    logger.info("Enhanced phishing detection models loaded successfully")
                    return True
                    
                except ImportError as e:
                    logger.warning(f"ML libraries not available: {e}. Using rule-based detection.")
                    model_cache["initialized"] = "fallback"
                    return True
                    
            else:
                logger.warning("Pre-trained model not found. Using rule-based detection.")
                model_cache["initialized"] = "fallback" 
                return True
                
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            model_cache["initialized"] = "fallback"
            return True
    
    def extract_advanced_features(self, email_text: str) -> Dict[str, Any]:
        """Extract comprehensive features from email text"""
        if not email_text:
            email_text = ""
        features = {}
        text_lower = email_text.lower()
        
        # URL Analysis
        url_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|short\.link',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        ]
        
        urls = []
        for pattern in url_patterns:
            urls.extend(re.findall(pattern, email_text, re.IGNORECASE))
        
        features['url_count'] = len(urls)
        features['suspicious_domains'] = sum(1 for url in urls if any(sus in url.lower() 
            for sus in ['bit.ly', 'tinyurl', 't.co', 'secure-', 'verify-', 'update-']))
        features['ip_urls'] = len(re.findall(r'https?://(?:\d{1,3}\.){3}\d{1,3}', email_text))
        
        # Urgency and Social Engineering Indicators
        urgency_words = [
            'urgent', 'immediate', 'asap', 'expires', 'deadline', 'limited time',
            'act now', 'hurry', 'final notice', 'last chance', 'time sensitive'
        ]
        features['urgency_score'] = sum(1 for word in urgency_words if word in text_lower)
        
        # Social Engineering Patterns
        social_eng_patterns = [
            'verify.*account', 'update.*information', 'confirm.*identity',
            'suspended.*account', 'unusual.*activity', 'security.*alert',
            'click.*here', 'download.*attachment', 'login.*immediately'
        ]
        features['social_engineering_score'] = sum(1 for pattern in social_eng_patterns 
            if re.search(pattern, text_lower))
        
        # Suspicious Phrases
        suspicious_phrases = [
            'congratulations', 'you.*won', 'claim.*prize', 'free.*money',
            'nigerian.*prince', 'inheritance', 'lottery.*winner', 'refund',
            'tax.*refund', 'irs.*refund', 'bank.*transfer'
        ]
        features['suspicious_phrases'] = sum(1 for phrase in suspicious_phrases 
            if re.search(phrase, text_lower))
        
        # Technical Indicators
        features['has_attachments'] = int('attachment' in text_lower or 'download' in text_lower)
        features['personal_info_request'] = sum(1 for term in ['ssn', 'social security', 'password', 
            'pin', 'credit card', 'bank account'] if term in text_lower)
        
        # Grammar and Spelling Analysis (simple)
        features['grammar_score'] = self.analyze_grammar_quality(email_text)
        features['length'] = len(email_text)
        features['caps_ratio'] = sum(1 for c in email_text if c.isupper()) / max(len(email_text), 1)
        
        return features
    
    def analyze_grammar_quality(self, text: str) -> float:
        """Simple grammar quality analysis"""
        if not text:
            return 0.0
        indicators = 0
        
        # Check for common grammar issues
        if re.search(r'\b(your|you\'re)\s+(account|information)\b', text.lower()):
            indicators += 1
        if re.search(r'\bteh\b|\brecieve\b|\boccured\b', text.lower()):  # Common typos
            indicators += 1
        if len(re.findall(r'[.!?]', text)) < len(text.split()) * 0.1:  # Few punctuation marks
            indicators += 1
        if text.count('!!!') > 0 or text.count('???') > 0:
            indicators += 1
        
        return min(indicators / 4.0, 1.0)  # Normalized score
    
    async def analyze_with_ml(self, email_text: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze email using ML model if available"""
        if model_cache["initialized"] != True:
            return await self.analyze_with_rules(email_text, features)
        
        try:
            # Get embeddings
            embedder = model_cache["embedder"]
            classifier = model_cache["classifier"]
            
            embedding = embedder.encode([email_text])
            
            # Prepare structured features (matching training format)
            structured_features = np.array([[
                features.get('url_count', 0),
                int(features.get('suspicious_domains', 0) > 0),
                features.get('urgency_score', 0)
            ]])
            
            # Combine features
            final_input = np.hstack([embedding, structured_features])
            
            # Predict
            prediction = classifier.predict(final_input)[0]
            probabilities = classifier.predict_proba(final_input)[0]
            confidence = probabilities[prediction] * 100
            
            return {
                'is_phishing': bool(prediction == 1),
                'confidence': confidence,
                'method': 'ml_model',
                'probabilities': probabilities.tolist()
            }
            
        except Exception as e:
            logger.error(f"ML analysis failed: {e}")
            return await self.analyze_with_rules(email_text, features)
    
    async def analyze_with_rules(self, email_text: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based analysis"""
        risk_score = 0
        risk_factors = []
        
        # URL-based scoring
        if features.get('url_count', 0) > 3:
            risk_score += 20
            risk_factors.append("Multiple URLs detected")
        
        if features.get('suspicious_domains', 0) > 0:
            risk_score += 30
            risk_factors.append("Suspicious URL shorteners detected")
        
        if features.get('ip_urls', 0) > 0:
            risk_score += 25
            risk_factors.append("URLs with IP addresses")
        
        # Social engineering scoring
        if features.get('urgency_score', 0) > 2:
            risk_score += 25
            risk_factors.append("High urgency language")
        
        if features.get('social_engineering_score', 0) > 1:
            risk_score += 30
            risk_factors.append("Social engineering patterns")
        
        if features.get('suspicious_phrases', 0) > 0:
            risk_score += 20
            risk_factors.append("Suspicious phrases detected")
        
        # Personal information requests
        if features.get('personal_info_request', 0) > 0:
            risk_score += 35
            risk_factors.append("Requests personal information")
        
        # Grammar and formatting
        if features.get('grammar_score', 0) > 0.5:
            risk_score += 15
            risk_factors.append("Poor grammar/spelling")
        
        if features.get('caps_ratio', 0) > 0.3:
            risk_score += 10
            risk_factors.append("Excessive capitalization")
        
        # Determine if phishing based on score
        is_phishing = risk_score >= 40
        confidence = min(risk_score * 1.5, 95)  # Convert to confidence percentage
        
        return {
            'is_phishing': is_phishing,
            'confidence': confidence,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'method': 'rule_based'
        }
    
    def get_risk_level(self, confidence: float, is_phishing: bool) -> str:
        """Determine risk level based on confidence"""
        if not is_phishing:
            return "LOW"
        elif confidence >= 90:
            return "CRITICAL"
        elif confidence >= 75:
            return "HIGH"
        elif confidence >= 50:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_recommendations(self, analysis_result: Dict[str, Any], features: Dict[str, Any]) -> List[str]:
        """Generate specific security recommendations"""
        recommendations = []
        
        if analysis_result['is_phishing']:
            recommendations.append("🚨 DO NOT click any links or download attachments")
            recommendations.append("📧 Report this email to your IT security team")
            recommendations.append("🗑️ Delete this email immediately")
            
            if features.get('url_count', 0) > 0:
                recommendations.append("⚠️ Verify any URLs independently before visiting")
            
            if features.get('personal_info_request', 0) > 0:
                recommendations.append("🔒 Never provide personal information via email")
            
            if 'social_engineering' in analysis_result.get('risk_factors', []):
                recommendations.append("🧠 Be aware of psychological manipulation tactics")
        else:
            recommendations.append("✅ Email appears safe, but remain vigilant")
            recommendations.append("🔍 Always verify sender identity for sensitive requests")
            recommendations.append("📝 When in doubt, contact the sender directly")
        
        return recommendations

# Initialize detector instance
detector = EnhancedPhishingDetector()

# FIXED: Remove router startup event and use lazy initialization
# @router.on_event("startup")  # This doesn't work reliably with dynamic imports
# async def startup_detector():
#     """Initialize the phishing detector on startup"""
#     await detector.initialize_models()

@router.post("/analyze", response_model=PhishingAnalysisResponse)
@router.post("/analyze-email", response_model=PhishingAnalysisResponse)
async def analyze_email(request: EmailAnalysisRequest):
    """Analyze email or URL content for phishing indicators"""
    start_time = time.time()
    text_content = request.email_content or request.url or request.content or ""
    
    try:
        # Check cache first
        if request.cache_results:
            email_hash = hashlib.md5(text_content.encode()).hexdigest()
            if email_hash in model_cache["prediction_cache"]:
                cached_result = model_cache["prediction_cache"][email_hash]
                if time.time() - model_cache["cache_expiry"].get(email_hash, 0) < 3600:  # 1 hour cache
                    logger.info(f"Returning cached result for email analysis")
                    return cached_result
        
        # Ensure models are initialized
        await detector.initialize_models()
        
        # Extract features
        features = detector.extract_advanced_features(text_content)
        
        # Analyze with available method
        analysis_result = await detector.analyze_with_ml(text_content, features)
        
        # Generate response
        risk_level = detector.get_risk_level(analysis_result['confidence'], analysis_result['is_phishing'])
        recommendations = detector.generate_recommendations(analysis_result, features)
        
        analysis_time = time.time() - start_time
        
        response = PhishingAnalysisResponse(
            is_phishing=analysis_result['is_phishing'],
            confidence_score=round(analysis_result['confidence'], 2),
            risk_level=risk_level,
            analysis_details={
                'features': features if request.include_detailed_analysis else {},
                'analysis_method': analysis_result.get('method', 'rule_based'),
                'risk_factors': analysis_result.get('risk_factors', []),
                'email_length': len(text_content),
                'processing_time_ms': round(analysis_time * 1000, 2)
            },
            recommendations=recommendations,
            analysis_time=round(analysis_time, 3),
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Cache result
        if request.cache_results:
            model_cache["prediction_cache"][email_hash] = response
            model_cache["cache_expiry"][email_hash] = time.time()
            
            # Clean old cache entries (keep last 100)
            if len(model_cache["prediction_cache"]) > 100:
                oldest_key = min(model_cache["cache_expiry"], key=model_cache["cache_expiry"].get)
                del model_cache["prediction_cache"][oldest_key]
                del model_cache["cache_expiry"][oldest_key]
        
        logger.info(f"Email analysis completed: {risk_level} risk, {analysis_result['confidence']:.1f}% confidence")
        return response
        
    except Exception as e:
        logger.error(f"Error in email analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/batch-analyze")
async def batch_analyze_emails(emails: List[EmailAnalysisRequest]):
    """Analyze multiple emails in batch"""
    if len(emails) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 emails per batch request")
    
    results = []
    for email_request in emails:
        try:
            result = await analyze_email(email_request)
            results.append(result)
        except Exception as e:
            results.append({
                "error": str(e),
                "email_content": email_request.email_content[:100] + "..." if len(email_request.email_content) > 100 else email_request.email_content
            })
    
    return {"results": results, "processed_count": len(results)}

@router.post("/initialize")
async def initialize_detector():
    """Manually initialize the phishing detector"""
    try:
        result = await detector.initialize_models()
        return {
            "status": "success",
            "initialized": result,
            "model_type": "ml_model" if model_cache["initialized"] == True else "rule_based",
            "classifier_loaded": model_cache["classifier"] is not None,
            "embedder_loaded": model_cache["embedder"] is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "initialized": False
        }

@router.get("/detector-status")
async def get_detector_status():
    """Get current status of the phishing detector"""
    return {
        "status": "healthy" if model_cache["initialized"] else "initializing",
        "model_type": "ml_model" if model_cache["initialized"] == True else "rule_based",
        "cache_size": len(model_cache["prediction_cache"]),
        "capabilities": {
            "url_analysis": True,
            "social_engineering_detection": True,
            "urgency_detection": True,
            "grammar_analysis": True,
            "ml_classification": model_cache["initialized"] == True,
            "batch_processing": True,
            "caching": True
        }
    }

@router.get("/health")
async def detector_health():
    """Health check for phishing detector"""
    return {
        "status": "healthy",
        "service": "phishing_detector",
        "version": "2.0.0",
        "endpoints": ["/analyze-email", "/batch-analyze", "/detector-status"],
        "model_initialized": model_cache["initialized"]
    }
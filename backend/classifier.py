"""
Intent Classifier for Phishy Platform

This module provides intent classification to route user queries between:
- CHAT: Educational questions, general cybersecurity discussions
- REPORT: Analytics, reporting, data queries, dashboard requests

Uses sentence-transformers for embeddings and scikit-learn for classification.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# ML imports
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except (ImportError, Exception) as e:
    SKLEARN_AVAILABLE = False
    logging.warning(f"scikit-learn not available or DLL blocked ({e}), using fallback method")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except (ImportError, Exception) as e:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning(f"sentence-transformers not available or DLL blocked ({e}), using fallback method")

logger = logging.getLogger(__name__)

class IntentClassifier:
    """
    Lightweight intent classifier for routing user queries.
    
    Uses sentence-transformers for embeddings and logistic regression for classification.
    Supports two intents: CHAT and REPORT.
    """
    
    def __init__(self, model_dir: str = "data/intent_model"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.model_dir / "intent_classifier.pkl"
        self.scaler_path = self.model_dir / "scaler.pkl" 
        self.dataset_path = Path("data/intent_dataset.csv")
        
        # Initialize components
        self.classifier: Optional[LogisticRegression] = None
        self.scaler: Optional[StandardScaler] = None
        self.encoder: Optional[SentenceTransformer] = None
        
        # Initialize sentence transformer
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ SentenceTransformer loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load SentenceTransformer: {e}")
                self.encoder = None
        
        # Load existing model if available
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load existing trained model and scaler"""
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                with open(self.model_path, 'rb') as f:
                    self.classifier = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("✅ Existing intent model loaded successfully")
                return True
        except Exception as e:
            logger.error(f"❌ Error loading existing model: {e}")
        
        return False
    
    def _save_model(self):
        """Save trained model and scaler"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.classifier, f)
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info("✅ Intent model saved successfully")
        except Exception as e:
            logger.error(f"❌ Error saving model: {e}")
    
    def generate_synthetic_training_data(self) -> List[Tuple[str, str]]:
        """
        Generate synthetic training examples for both CHAT and REPORT intents.
        
        Returns list of (query, label) tuples.
        """
        
        # CHAT examples - educational, general questions
        chat_examples = [
            # Basic cybersecurity questions
            "What is phishing?",
            "How does social engineering work?",
            "What are the types of cyberattacks?",
            "Explain malware and viruses",
            "What is ransomware?",
            "How to create strong passwords?",
            "What is two-factor authentication?",
            "Tell me about email security",
            "How to spot fake emails?",
            "What are cybersecurity best practices?",
            
            # Conversational queries
            "Hello, can you help me?",
            "Hi there!",
            "Good morning",
            "Can you explain cybersecurity to me?",
            "I need help understanding threats",
            "What should I know about online safety?",
            "How can I protect myself online?",
            "What are the latest cyber threats?",
            "Can you teach me about security awareness?",
            "I want to learn about phishing detection",
            
            # Educational requests
            "Explain the difference between phishing and spear phishing",
            "How do hackers steal personal information?",
            "What is a security awareness training?",
            "How to recognize suspicious websites?",
            "What are the signs of a phishing email?",
            "How does encryption work?",
            "What is endpoint security?",
            "Tell me about network security",
            "How to secure mobile devices?",
            "What are security certificates?",
            
            # General help
            "I have a question about cybersecurity",
            "Can you help me understand threats?",
            "What do you recommend for security?",
            "How can organizations improve security?",
            "What are common security mistakes?",
            "How to train employees on security?",
            "What is security culture?",
            "How to respond to incidents?",
            "What are security policies?",
            "How to assess security risks?"
        ]
        
        # REPORT examples - analytics, data queries, reporting
        report_examples = [
            # Click analytics
            "Show me click trends",
            "What are the current click statistics?",
            "Display click analytics",
            "Generate click report",
            "How many clicks this week?",
            "Who clicked the most links?",
            "Show user activity data",
            "Current click metrics",
            "Click tracking dashboard",
            "Recent click activity",
            
            # User analysis
            "Which users are most vulnerable?",
            "Show top clicking users",
            "User behavior analysis",
            "Display user statistics",
            "Who needs more training?",
            "Show risk assessment by user",
            "Generate user activity report",
            "List most active users",
            "User engagement metrics",
            "Show training effectiveness",
            
            # Email tracking
            "Email open rates",
            "Show flagged emails",
            "Display email tracking data",
            "How many emails were flagged?",
            "Email security metrics",
            "Generate flagged email report",
            "Show email analytics",
            "Track email performance",
            "Display email statistics",
            "Email campaign results",
            
            # General reporting
            "Generate security report",
            "Show dashboard",
            "Display analytics",
            "Current security status",
            "Show metrics",
            "Generate summary report",
            "Display statistics",
            "Show trends",
            "Analytics overview",
            "Security posture report",
            
            # Specific data requests
            "Show me the data",
            "Display current stats",
            "What's the status?",
            "Generate CSV report",
            "Export analytics data",
            "Show recent activity",
            "Display logs",
            "Current numbers",
            "Show performance metrics",
            "Generate weekly report"
        ]
        
        # Combine and create training data
        training_data = []
        training_data.extend([(query, "CHAT") for query in chat_examples])
        training_data.extend([(query, "REPORT") for query in report_examples])
        
        logger.info(f"Generated {len(training_data)} synthetic training examples")
        logger.info(f"  CHAT examples: {len(chat_examples)}")
        logger.info(f"  REPORT examples: {len(report_examples)}")
        
        return training_data
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts using sentence transformer or fallback"""
        if self.encoder is not None:
            try:
                embeddings = self.encoder.encode(texts, show_progress_bar=False)
                return embeddings
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
        
        # Fallback to simple feature extraction if sentence-transformers unavailable
        logger.warning("Using fallback feature extraction (bag of words)")
        return self._fallback_features(texts)
    
    def _fallback_features(self, texts: List[str]) -> np.ndarray:
        """
        Fallback feature extraction using keyword matching.
        Used when sentence-transformers is not available.
        """
        report_keywords = {
            'click', 'user', 'show', 'display', 'generate', 'report', 'analytics', 
            'metrics', 'statistics', 'data', 'dashboard', 'activity', 'trends',
            'status', 'numbers', 'flagged', 'tracking', 'performance', 'logs'
        }
        
        chat_keywords = {
            'what', 'how', 'explain', 'tell', 'help', 'learn', 'understand',
            'phishing', 'security', 'cybersecurity', 'threat', 'attack', 'safe',
            'protect', 'awareness', 'training', 'best', 'practices'
        }
        
        features = []
        for text in texts:
            text_lower = text.lower()
            words = set(text_lower.split())
            
            feature_vector = [
                len(words & report_keywords),  # Report keyword count
                len(words & chat_keywords),    # Chat keyword count
                len([w for w in words if w.endswith('?')]),  # Question words
                1 if any(w in text_lower for w in ['show', 'display', 'generate']) else 0,
                1 if any(w in text_lower for w in ['what', 'how', 'why']) else 0,
                len(text),  # Text length
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Load or generate training data and return features and labels"""
        
        # Check for existing dataset
        if self.dataset_path.exists():
            try:
                df = pd.read_csv(self.dataset_path)
                if len(df) >= 20:  # Minimum viable dataset
                    logger.info(f"✅ Loaded existing dataset with {len(df)} examples")
                    queries = df['query'].tolist()
                    labels = df['label'].tolist()
                else:
                    logger.info("Existing dataset too small, generating synthetic data")
                    training_data = self.generate_synthetic_training_data()
                    queries, labels = zip(*training_data)
            except Exception as e:
                logger.error(f"Error loading existing dataset: {e}")
                training_data = self.generate_synthetic_training_data()
                queries, labels = zip(*training_data)
        else:
            logger.info("No existing dataset found, generating synthetic data")
            training_data = self.generate_synthetic_training_data()
            queries, labels = zip(*training_data)
            
            # Save generated dataset for future use and expansion
            df = pd.DataFrame({'query': queries, 'label': labels})
            df.to_csv(self.dataset_path, index=False)
            logger.info(f"💾 Saved training dataset to {self.dataset_path}")
        
        # Generate embeddings
        logger.info("Generating embeddings for training data...")
        X = self._get_embeddings(list(queries))
        y = np.array(labels)
        
        return X, y
    
    def train(self, force_retrain: bool = False):
        """Train the intent classifier"""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn is not available or DLL blocked. Using fallback prediction.")
            return

        if not force_retrain and self.classifier is not None:
            logger.info("✅ Model already loaded, skipping training")
            return
        
        logger.info("🏋️ Training intent classifier...")
        
        # Prepare data
        X, y = self.prepare_training_data()
        
        if len(X) == 0:
            raise ValueError("No training data available")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train classifier
        self.classifier = LogisticRegression(
            random_state=42,
            max_iter=1000,
            class_weight='balanced'  # Handle class imbalance
        )
        
        self.classifier.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.classifier.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"✅ Training completed!")
        logger.info(f"   Training samples: {len(X_train)}")
        logger.info(f"   Test accuracy: {accuracy:.3f}")
        
        # Detailed classification report
        report = classification_report(y_test, y_pred, output_dict=True)
        logger.info(f"   CHAT precision: {report['CHAT']['precision']:.3f}")
        logger.info(f"   REPORT precision: {report['REPORT']['precision']:.3f}")
        
        # Save model
        self._save_model()
        
        logger.info("🎉 Intent classifier ready for use!")
    
    def predict_intent(self, query: str) -> str:
        """
        Predict intent for a user query.
        
        Args:
            query: User input string
            
        Returns:
            "CHAT" or "REPORT"
        """
        if self.classifier is None or self.scaler is None:
            logger.warning("Model not trained, training now...")
            self.train()
        
        if self.classifier is None:
            logger.error("Failed to train model, using fallback")
            return self._fallback_prediction(query)
        
        try:
            # Generate embedding
            embedding = self._get_embeddings([query])
            
            # Scale and predict
            embedding_scaled = self.scaler.transform(embedding)
            prediction = self.classifier.predict(embedding_scaled)[0]
            
            # Get confidence
            probabilities = self.classifier.predict_proba(embedding_scaled)[0]
            confidence = max(probabilities)
            
            logger.debug(f"Query: '{query}' -> {prediction} (confidence: {confidence:.3f})")
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting intent: {e}")
            return self._fallback_prediction(query)
    
    def _fallback_prediction(self, query: str) -> str:
        """Fallback intent prediction using keyword matching"""
        query_lower = query.lower()
        
        # Report indicators
        report_keywords = [
            'show', 'display', 'generate', 'report', 'analytics', 'metrics', 
            'statistics', 'data', 'dashboard', 'click', 'user', 'activity',
            'trends', 'status', 'flagged', 'tracking', 'logs', 'numbers'
        ]
        
        # Chat indicators  
        chat_keywords = [
            'what', 'how', 'explain', 'tell', 'help', 'learn', 'understand',
            'phishing', 'cybersecurity', 'threat', 'attack', 'security',
            'hello', 'hi', 'good', 'morning', 'afternoon'
        ]
        
        report_score = sum(1 for kw in report_keywords if kw in query_lower)
        chat_score = sum(1 for kw in chat_keywords if kw in query_lower)
        
        if report_score > chat_score:
            return "REPORT"
        else:
            return "CHAT"
    
    def get_model_info(self) -> dict:
        """Get information about the current model"""
        return {
            "model_loaded": self.classifier is not None,
            "encoder_available": self.encoder is not None,
            "model_type": "LogisticRegression" if self.classifier else None,
            "embedding_model": "all-MiniLM-L6-v2" if self.encoder else "fallback",
            "dataset_path": str(self.dataset_path),
            "model_path": str(self.model_path),
            "last_trained": datetime.now().isoformat() if self.classifier else None
        }


# Global classifier instance
_classifier = None

def get_classifier() -> IntentClassifier:
    """Get global classifier instance (singleton pattern)"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
        # Auto-train on first use if needed
        if _classifier.classifier is None:
            _classifier.train()
    return _classifier

def predict_intent(query: str) -> str:
    """
    Main function to predict intent for a query.
    
    Args:
        query: User input string
        
    Returns:
        "CHAT" or "REPORT"
    """
    classifier = get_classifier()
    return classifier.predict_intent(query)

# Test function for development
def test_classifier():
    """Test the classifier with sample queries"""
    classifier = get_classifier()
    
    test_queries = [
        "What is phishing?",  # Should be CHAT
        "Show click trends",  # Should be REPORT 
        "Hello, how are you?",  # Should be CHAT
        "Generate analytics report",  # Should be REPORT
        "Explain cybersecurity",  # Should be CHAT
        "Display user statistics"  # Should be REPORT
    ]
    
    print("\nTesting Intent Classifier:")
    print("-" * 40)
    
    for query in test_queries:
        intent = classifier.predict_intent(query)
        print(f"'{query}' -> {intent}")
    
    print("-" * 40)
    print("Model Info:", classifier.get_model_info())

if __name__ == "__main__":
    test_classifier()
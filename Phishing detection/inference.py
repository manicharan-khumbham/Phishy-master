# inference.py

from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier
import numpy as np

# Load model
classifier = XGBClassifier()
import os
model_path = os.path.join(os.path.dirname(__file__), 'model', 'xgb_model.json')
classifier.load_model(model_path)

# Load embedder
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Original feature extraction (matching training data)
def extract_structured_features(email_text):
    text_lower = email_text.lower()
    
    # URL analysis
    url_count = text_lower.count('http')
    suspicious_urls = int(any(sub in text_lower for sub in ['bit.ly', 'tinyurl', 't.co', 'goo.gl', 'ow.ly']))
    
    # Urgent/phishing keywords - ORIGINAL SET
    urgent_words = ['urgent', 'verify', 'account', 'immediately', 'suspended']
    urgent_score = sum(1 for word in urgent_words if word in text_lower)
    
    # Return ORIGINAL 3 features that match training data
    return [
        url_count,           # 0
        suspicious_urls,     # 1  
        urgent_score,        # 2
    ]

# Classification function with debugging
def classify_email(email_text):
    print(f"[EMAIL] Analyzing email: {email_text[:100]}...")
    
    # Embedding
    embedding = embedder.encode([email_text])
    print(f"[EMBEDDING] Shape: {embedding.shape}")
    
    # Structured features
    structured_features = np.array([extract_structured_features(email_text)])
    print(f"[FEATURES] Structured features: {structured_features[0]}")
    
    # Combine
    final_input = np.hstack([embedding, structured_features])
    print(f"[INPUT] Final input shape: {final_input.shape}")
    
    # Get probabilities for both classes
    probabilities = classifier.predict_proba(final_input)[0]
    print(f"[PROBABILITIES] Safe={probabilities[0]:.3f}, Phishing={probabilities[1]:.3f}")
    
    # Use model's default prediction (it works correctly now with proper features)
    prediction = classifier.predict(final_input)[0]
    confidence = probabilities[prediction] * 100
    
    print(f"[PREDICTION] Model prediction: {prediction} (confidence: {confidence:.2f}%)")
    
    # Clear result message
    if prediction == 1:
        result = "*** PHISHING EMAIL DETECTED! ***"
    else:
        result = "*** Safe Email ***"
    
    return f"{result}\nConfidence: {confidence:.2f}%\nPhishing Probability: {probabilities[1]:.3f}"

# Example usage
if __name__ == "__main__":
    test_email = input("Paste email text to classify:\n")
    result = classify_email(test_email)
    print("\n" + result)

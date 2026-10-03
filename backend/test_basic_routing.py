#!/usr/bin/env python3
"""
Basic test for intelligent query routing without complex dependencies
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from classifier import predict_intent

def test_basic_routing():
    """Test basic intent classification and routing logic"""
    
    test_cases = [
        # CHAT examples
        ("What is phishing?", "CHAT", "Educational question"),
        ("Hello, how are you?", "CHAT", "Greeting"),
        ("Explain cybersecurity", "CHAT", "Educational request"),
        ("How does social engineering work?", "CHAT", "Technical question"),
        
        # REPORT examples
        ("Show click trends", "REPORT", "Analytics request"),
        ("Generate security report", "REPORT", "Report generation"),
        ("Display analytics", "REPORT", "Data display"),
        ("Which users clicked most?", "REPORT", "User analysis"),
    ]
    
    print("Testing Basic Intent Classification & Routing")
    print("=" * 50)
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for query, expected_intent, description in test_cases:
        predicted_intent = predict_intent(query)
        
        success = predicted_intent == expected_intent
        status = "PASS" if success else "FAIL"
        
        if success:
            correct_predictions += 1
        
        print(f"{status} {query}")
        print(f"     Expected: {expected_intent} | Predicted: {predicted_intent}")
        print(f"     Type: {description}")
        print()
    
    accuracy = (correct_predictions / total_tests) * 100
    print(f"Accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
    
    if accuracy >= 80:
        print("Intent classifier is working well!")
    else:
        print("Intent classifier needs improvement")
    
    return accuracy >= 80

if __name__ == "__main__":
    success = test_basic_routing()
    exit(0 if success else 1)
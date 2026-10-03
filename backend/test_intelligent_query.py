#!/usr/bin/env python3
"""
Test script for the intelligent query system
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from routes.intelligent_query import IntelligentQueryRequest, intelligent_query

async def test_intelligent_queries():
    """Test the intelligent query system with various inputs"""
    
    test_cases = [
        # CHAT queries - should go to LLM
        {
            "query": "What is phishing and how can I protect myself?",
            "expected_intent": "CHAT",
            "description": "Educational question about phishing"
        },
        {
            "query": "Hello, can you explain cybersecurity to me?",
            "expected_intent": "CHAT", 
            "description": "Greeting with educational request"
        },
        {
            "query": "How does social engineering work?",
            "expected_intent": "CHAT",
            "description": "Technical educational question"
        },
        
        # REPORT queries - should go to analytics/reporting  
        {
            "query": "Show me the current click trends",
            "expected_intent": "REPORT",
            "description": "Click analytics request"
        },
        {
            "query": "Generate a security status report",
            "expected_intent": "REPORT", 
            "description": "Status report request"
        },
        {
            "query": "Which users clicked the most links?",
            "expected_intent": "REPORT",
            "description": "User analysis query"
        }
    ]
    
    print("Testing Intelligent Query System")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print(f"Expected: {test_case['expected_intent']}")
        
        try:
            request = IntelligentQueryRequest(
                query=test_case['query'],
                temperature=0.7,
                max_tokens=200  # Shorter for testing
            )
            
            response = await intelligent_query(request)
            
            print(f"Predicted: {response.predicted_intent}")
            print(f"Route: {response.response_type}")
            print(f"Model: {response.model_used}")
            print(f"Time: {response.generation_time_ms}ms")
            
            # Check if prediction matches expectation
            success = response.predicted_intent == test_case['expected_intent']
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"Result: {status}")
            
            # Show first part of response
            response_preview = response.response[:100] + "..." if len(response.response) > 100 else response.response
            print(f"Response: {response_preview}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_intelligent_queries())
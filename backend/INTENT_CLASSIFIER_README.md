# Phishy Intent Classifier

## Overview
The Phishy platform now includes an intelligent query routing system that automatically classifies user queries and routes them to appropriate handlers:

- **CHAT**: Educational questions, cybersecurity discussions → Routed to Phi-3 Mini LLM
- **REPORT**: Analytics, reporting, data queries → Routed to structured data/templates

## Architecture

```
User Query → Intent Classifier → Route Decision
                   ↓                    ↓
            [CHAT] or [REPORT]     Appropriate Handler
                                          ↓
                               Structured Response
```

## Files Added/Modified

### New Files:
- `backend/classifier.py` - Intent classification module
- `backend/routes/intelligent_query.py` - Smart routing endpoint
- `backend/data/intent_dataset.csv` - Training data (auto-generated)
- `backend/data/intent_model/` - Trained model files
- `backend/requirements_classifier.txt` - Additional dependencies

### Modified Files:
- `backend/app.py` - Added intelligent query route

## API Endpoints

### Main Endpoint
```
POST /ai/intelligent-query
{
  "query": "What is phishing?",
  "temperature": 0.7,
  "max_tokens": 500,
  "include_analytics": true
}
```

**Response:**
```json
{
  "query": "What is phishing?",
  "predicted_intent": "CHAT",
  "response": "Phishing is a cybercrime where...",
  "response_type": "llm_chat",
  "model_used": "phi3:mini",
  "generation_time_ms": 1234,
  "timestamp": "2025-08-20T20:00:00Z"
}
```

### Utility Endpoints
- `GET /ai/classifier/info` - Classifier information
- `POST /ai/classifier/predict` - Direct intent prediction
- `POST /ai/classifier/retrain` - Retrain classifier

## Usage Examples

### CHAT Queries (→ LLM):
```
"What is phishing?"
"How does social engineering work?"
"Hello, can you help me with cybersecurity?"
"Explain two-factor authentication"
```

### REPORT Queries (→ Analytics):
```
"Show click trends"
"Generate security report" 
"Which users need more training?"
"Display current analytics"
```

## Technical Details

### Intent Classifier:
- **Model**: Logistic Regression with balanced class weights
- **Features**: Sentence embeddings from `all-MiniLM-L6-v2`
- **Training Data**: 90 synthetic examples (40 CHAT, 50 REPORT)
- **Fallback**: Keyword-based classification if sentence-transformers unavailable

### Response Routing:
- **CHAT Intent**: Routes to `/llm/chat` endpoint with Phi-3 Mini
- **REPORT Intent**: Routes to structured data handlers:
  - Click reports → `click_tracker.py`
  - Analytics → `analytics.py` 
  - Status reports → Structured templates
  - Complex queries → `admin_assistant.py`

## Installation

1. **Install Dependencies:**
   ```bash
   pip install scikit-learn>=1.3.0 sentence-transformers>=2.2.0
   ```

2. **Auto-Training:**
   - Classifier trains automatically on first use
   - Generates synthetic training data if none exists
   - Saves model to `data/intent_model/`

3. **Integration:**
   - Module is automatically loaded in `app.py`
   - Available at `/ai/intelligent-query` endpoint

## Expanding the Dataset

To improve classification accuracy:

1. **Add Real Examples:**
   ```python
   # Edit data/intent_dataset.csv
   query,label
   "Your real user query",CHAT
   "Another real query",REPORT
   ```

2. **Retrain Model:**
   ```bash
   curl -X POST http://localhost:8080/ai/classifier/retrain
   ```

3. **Monitor Performance:**
   ```python
   from classifier import get_classifier
   classifier = get_classifier()
   print(classifier.get_model_info())
   ```

## Frontend Integration

Update your frontend to use the intelligent query endpoint:

```javascript
// Replace direct /llm/chat or /admin/query calls with:
const response = await fetch(`${API_BASE}/ai/intelligent-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        query: userMessage,
        temperature: 0.7,
        max_tokens: 500
    })
});

const data = await response.json();
console.log(`Query routed to: ${data.response_type}`);
displayResponse(data.response);
```

## Benefits

1. **Automatic Routing**: No need for hardcoded frontend logic
2. **Consistent Experience**: Unified endpoint for all query types  
3. **Extensible**: Easy to add new intent types
4. **Performance**: Efficient routing reduces unnecessary LLM calls
5. **Scalable**: Can handle growing complexity of query types

## Monitoring

Check classifier performance:
```bash
curl http://localhost:8080/ai/classifier/info
```

View training data:
```bash
head -10 backend/data/intent_dataset.csv
```

## Future Enhancements

- Add more intent types (HELP, SETTINGS, etc.)
- Implement confidence thresholds
- A/B testing for routing decisions
- Real-time retraining with user feedback
- Multi-language support
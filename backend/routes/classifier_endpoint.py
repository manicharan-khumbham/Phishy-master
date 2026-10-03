import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from classifier import predict_intent

router = APIRouter()
logger = logging.getLogger(__name__)

class PredictRequest(BaseModel):
    query: str

class PredictResponse(BaseModel):
    query: str
    predicted_intent: str

@router.post("/predict", response_model=PredictResponse)
async def predict_intent_endpoint(request: PredictRequest):
    """Simple intent prediction endpoint"""
    try:
        intent = predict_intent(request.query)
        return PredictResponse(
            query=request.query,
            predicted_intent=intent
        )
    except Exception as e:
        logger.error(f"Intent prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/info")
async def classifier_info():
    """Get classifier info"""
    try:
        from classifier import get_classifier
        classifier = get_classifier()
        return {
            "status": "operational",
            "model_info": classifier.get_model_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classifier error: {str(e)}")
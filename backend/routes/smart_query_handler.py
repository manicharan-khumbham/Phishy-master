"""
Smart Query Handler for Phishy Platform

This module provides intelligent, context-aware responses to user queries about 
click trends and recent activity by actually fetching and analyzing the relevant data.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import os
import json

# Import existing components
try:
    from .llm_generator import OllamaClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)

class SmartQueryRequest(BaseModel):
    query: str = Field(..., description="User's natural language query")
    include_raw_data: Optional[bool] = Field(False, description="Include raw data in response")
    max_results: Optional[int] = Field(20, description="Maximum number of data points to analyze")

class SmartQueryResponse(BaseModel):
    query: str
    response: str
    data_analyzed: Dict[str, Any]
    insights: List[str]
    query_type: str
    timestamp: str

class SmartDataFetcher:
    """Intelligently fetches and analyzes data based on query context"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.click_logs_file = self.data_dir / "click_logs.csv"
        
    def get_recent_clicks(self, hours: int = 24, limit: Optional[int] = None) -> pd.DataFrame:
        """Get recent click data directly from SQLite Database"""
        try:
            from database import get_db_connection
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT timestamp, user_email, action_id, ip_address, user_agent, referer FROM click_logs", conn)
            conn.close()
            if df.empty:
                return df
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_df = df[df['timestamp'] >= cutoff_time]
            
            # Sort by timestamp descending (most recent first)
            recent_df = recent_df.sort_values('timestamp', ascending=False)
            
            if limit:
                recent_df = recent_df.head(limit)
                
            return recent_df
            
        except Exception as e:
            logger.error(f"Error fetching recent clicks from SQLite DB: {e}")
            return pd.DataFrame()
    
    def get_user_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get user activity patterns directly from SQLite Database"""
        try:
            from database import get_db_connection
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT timestamp, user_email, action_id, ip_address, user_agent, referer FROM click_logs", conn)
            conn.close()
            if df.empty:
                return {"users": [], "total_users": 0, "total_clicks": 0}
            if df.empty:
                return {"users": [], "total_users": 0, "total_clicks": 0}
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            recent_df = df[df['timestamp'] >= cutoff_time]
            
            # Analyze user patterns
            user_activity = recent_df.groupby('user_email').agg({
                'timestamp': ['count', 'min', 'max'],
                'action_id': 'nunique',
                'ip_address': 'nunique'
            }).round(2)
            
            user_summary = []
            for user in user_activity.index:
                clicks = user_activity.loc[user, ('timestamp', 'count')]
                first_click = user_activity.loc[user, ('timestamp', 'min')]
                last_click = user_activity.loc[user, ('timestamp', 'max')]
                unique_actions = user_activity.loc[user, ('action_id', 'nunique')]
                
                # Calculate time since last click
                if pd.notna(last_click):
                    time_since_last = datetime.utcnow() - pd.to_datetime(last_click)
                    hours_since = int(time_since_last.total_seconds() / 3600)
                else:
                    hours_since = None
                
                user_summary.append({
                    "email": user,
                    "total_clicks": int(clicks),
                    "unique_actions": int(unique_actions),
                    "first_click": pd.to_datetime(first_click).isoformat() if pd.notna(first_click) else None,
                    "last_click": pd.to_datetime(last_click).isoformat() if pd.notna(last_click) else None,
                    "hours_since_last_click": hours_since,
                    "risk_level": "HIGH" if clicks > 3 else "MEDIUM" if clicks > 1 else "LOW"
                })
            
            # Sort by most recent activity
            user_summary.sort(key=lambda x: x['last_click'] or '', reverse=True)
            
            return {
                "users": user_summary,
                "total_users": len(user_summary),
                "total_clicks": int(recent_df['user_email'].count()),
                "time_period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user activity: {e}")
            return {"users": [], "total_users": 0, "total_clicks": 0, "error": str(e)}
    
    def get_click_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze click trends over time"""
        try:
            if not self.click_logs_file.exists():
                return {"trends": [], "summary": "No data available"}
            
            df = pd.read_csv(self.click_logs_file)
            if df.empty:
                return {"trends": [], "summary": "No data available"}
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            recent_df = df[df['timestamp'] >= cutoff_time]
            
            # Daily trends
            daily_clicks = recent_df.groupby(recent_df['timestamp'].dt.date).size()
            
            # Hourly patterns
            hourly_pattern = recent_df.groupby(recent_df['timestamp'].dt.hour).size()
            
            # Weekly patterns
            weekly_pattern = recent_df.groupby(recent_df['timestamp'].dt.day_name()).size()
            
            trends = {
                "daily_clicks": {str(k): int(v) for k, v in daily_clicks.items()},
                "peak_hour": int(hourly_pattern.idxmax()) if not hourly_pattern.empty else None,
                "peak_day": str(weekly_pattern.idxmax()) if not weekly_pattern.empty else None,
                "total_clicks_period": len(recent_df),
                "average_daily_clicks": round(len(recent_df) / max(days, 1), 2),
                "most_active_users": {str(k): int(v) for k, v in recent_df['user_email'].value_counts().head(5).items()}
            }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {"trends": [], "summary": f"Error analyzing trends: {e}"}

class SmartQueryAnalyzer:
    """Analyzes user queries to determine what data to fetch and how to respond"""
    
    def __init__(self):
        self.data_fetcher = SmartDataFetcher()
        if LLM_AVAILABLE:
            self.llm_client = OllamaClient()
        else:
            self.llm_client = None
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Determine what the user is asking for"""
        query_lower = query.lower()
        
        intent = {
            "type": "general",
            "time_scope": "recent",
            "focus": "activity",
            "specific_user": None,
            "needs_real_data": True
        }
        
        # Detect query type
        if any(word in query_lower for word in ["who", "which users", "users who"]):
            intent["type"] = "user_identification"
        elif any(word in query_lower for word in ["trend", "pattern", "over time", "daily", "weekly"]):
            intent["type"] = "trend_analysis"
        elif any(word in query_lower for word in ["recent", "lately", "today", "yesterday"]):
            intent["type"] = "recent_activity"
        elif any(word in query_lower for word in ["total", "count", "how many", "statistics"]):
            intent["type"] = "statistics"
        
        # Detect time scope
        if any(word in query_lower for word in ["today", "24 hours", "24h"]):
            intent["time_scope"] = "24h"
        elif any(word in query_lower for word in ["week", "7 days", "7d", "weekly"]):
            intent["time_scope"] = "7d"
        elif any(word in query_lower for word in ["month", "30 days", "30d", "monthly"]):
            intent["time_scope"] = "30d"
        elif any(word in query_lower for word in ["recent", "lately", "recently"]):
            intent["time_scope"] = "recent"
        
        # Check for specific user mention
        if "@" in query:
            # Extract potential email
            words = query.split()
            for word in words:
                if "@" in word:
                    intent["specific_user"] = word
                    break
        
        return intent
    
    async def generate_smart_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate contextual response using LLM with real data"""
        
        if not self.llm_client:
            return self._generate_fallback_response(query, intent, data)
        
        try:
            # Create data summary for LLM
            data_summary = self._create_data_summary(data, intent)
            
            prompt = f"""You are a cybersecurity analyst assistant. The user asked: "{query}"

Here is the ACTUAL, REAL-TIME data from our phishing simulation platform:

{data_summary}

Based on this REAL data, provide a helpful, specific response that:
1. Directly answers their question using the actual data
2. Provides specific details (names, numbers, times) from the data
3. Offers security insights based on the patterns you see
4. Is conversational and helpful, not template-like

Do NOT use generic templates. Use the actual data provided above.
Be specific about what the data shows."""

            response = await self.llm_client.generate_completion(
                prompt, 
                max_tokens=400, 
                temperature=0.3  # Lower temperature for more factual responses
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._generate_fallback_response(query, intent, data)
    
    def _create_data_summary(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Create a concise data summary for the LLM"""
        summary_parts = []
        
        if "recent_clicks" in data and not data["recent_clicks"].empty:
            recent_df = data["recent_clicks"]
            summary_parts.append(f"RECENT CLICKS ({len(recent_df)} total):")
            
            for idx, row in recent_df.head(10).iterrows():
                time_ago = datetime.utcnow() - pd.to_datetime(row['timestamp'])
                hours_ago = int(time_ago.total_seconds() / 3600)
                summary_parts.append(f"- {row['user_email']} clicked {hours_ago}h ago (Action: {row['action_id']})")
        
        if "user_activity" in data:
            activity = data["user_activity"]
            summary_parts.append(f"\nUSER ACTIVITY SUMMARY:")
            summary_parts.append(f"- Total users active: {activity.get('total_users', 0)}")
            summary_parts.append(f"- Total clicks: {activity.get('total_clicks', 0)}")
            
            for user in activity.get("users", [])[:5]:
                summary_parts.append(f"- {user['email']}: {user['total_clicks']} clicks, last click {user['hours_since_last_click']}h ago")
        
        if "trends" in data:
            trends = data["trends"]
            summary_parts.append(f"\nTREND ANALYSIS:")
            summary_parts.append(f"- Peak hour: {trends.get('peak_hour', 'N/A')}:00")
            summary_parts.append(f"- Most active day: {trends.get('peak_day', 'N/A')}")
            summary_parts.append(f"- Average daily clicks: {trends.get('average_daily_clicks', 0)}")
        
        return "\n".join(summary_parts)
    
    def _generate_fallback_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate response without LLM using actual data"""
        
        if intent["type"] == "recent_activity" and "recent_clicks" in data:
            recent_df = data["recent_clicks"]
            if recent_df.empty:
                return "No recent click activity found in the phishing simulation data."
            
            response_parts = [f"Based on real-time data, here are the {len(recent_df)} most recent clicks:"]
            
            for idx, row in recent_df.head(10).iterrows():
                time_ago = datetime.utcnow() - pd.to_datetime(row['timestamp'])
                hours_ago = int(time_ago.total_seconds() / 3600)
                mins_ago = int((time_ago.total_seconds() % 3600) / 60)
                
                if hours_ago > 0:
                    time_str = f"{hours_ago}h ago"
                else:
                    time_str = f"{mins_ago}m ago"
                
                response_parts.append(f"• {row['user_email']} - {time_str}")
            
            if len(recent_df) > 10:
                response_parts.append(f"... and {len(recent_df) - 10} more clicks")
            
            return "\n".join(response_parts)
        
        elif intent["type"] == "user_identification" and "user_activity" in data:
            activity = data["user_activity"]
            users = activity.get("users", [])
            
            if not users:
                return "No user activity found in the specified time period."
            
            response_parts = [f"Here are the {len(users)} users who clicked on phishing emails recently:"]
            
            for user in users[:10]:
                risk_emoji = "🔴" if user["risk_level"] == "HIGH" else "🟡" if user["risk_level"] == "MEDIUM" else "🟢"
                response_parts.append(f"{risk_emoji} {user['email']} - {user['total_clicks']} clicks, last activity {user['hours_since_last_click']}h ago")
            
            return "\n".join(response_parts)
        
        else:
            return f"I analyzed the data for your query '{query}', but couldn't generate a specific response. Please try asking about recent clicks or user activity."

# Initialize the smart analyzer
smart_analyzer = SmartQueryAnalyzer()

@router.post("/smart-query", response_model=SmartQueryResponse)
async def handle_smart_query(request: SmartQueryRequest):
    """
    Handle intelligent queries about click data and user activity.
    
    This endpoint analyzes the user's natural language query, fetches the relevant
    real-time data, and generates a contextual response using actual data instead
    of templates.
    """
    try:
        # Analyze what the user is asking for
        intent = smart_analyzer.analyze_query_intent(request.query)
        logger.info(f"Query intent: {intent} for query: '{request.query}'")
        
        # Fetch the appropriate data based on intent
        data = {}
        insights = []
        
        if intent["type"] in ["recent_activity", "user_identification"]:
            # Get recent clicks
            hours = 24 if intent["time_scope"] == "24h" else 168 if intent["time_scope"] == "7d" else 24
            recent_clicks = smart_analyzer.data_fetcher.get_recent_clicks(
                hours=hours, 
                limit=request.max_results
            )
            data["recent_clicks"] = recent_clicks
            
            if not recent_clicks.empty:
                insights.append(f"Found {len(recent_clicks)} recent clicks in the last {hours} hours")
                insights.append(f"Most recent click was from {recent_clicks.iloc[0]['user_email']}")
        
        if intent["type"] in ["user_identification", "statistics"]:
            # Get user activity summary
            days = 1 if intent["time_scope"] == "24h" else 7 if intent["time_scope"] == "7d" else 30 if intent["time_scope"] == "30d" else 7
            user_activity = smart_analyzer.data_fetcher.get_user_activity_summary(days=days)
            data["user_activity"] = user_activity
            
            if user_activity["total_users"] > 0:
                insights.append(f"Total of {user_activity['total_users']} users clicked in the last {days} days")
                high_risk_users = [u for u in user_activity["users"] if u["risk_level"] == "HIGH"]
                if high_risk_users:
                    insights.append(f"{len(high_risk_users)} users are classified as HIGH risk")
        
        if intent["type"] == "trend_analysis":
            # Get trend analysis
            days = 7 if intent["time_scope"] == "7d" else 30 if intent["time_scope"] == "30d" else 30
            trends = smart_analyzer.data_fetcher.get_click_trends(days=days)
            data["trends"] = trends
            
            if trends.get("peak_hour") is not None:
                insights.append(f"Peak activity hour is {trends['peak_hour']}:00")
            if trends.get("peak_day"):
                insights.append(f"Most active day is {trends['peak_day']}")
        
        # Generate smart response using real data
        response_text = await smart_analyzer.generate_smart_response(
            request.query, 
            intent, 
            data
        )
        
        # Clean up data for response to guarantee JSON serializability
        clean_data = {}
        for k, v in data.items():
            if isinstance(v, pd.DataFrame):
                clean_data[k] = v.to_dict('records') if request.include_raw_data else {"count": len(v), "summary": "DataFrame with click data"}
            else:
                clean_data[k] = v
        data = clean_data

        return SmartQueryResponse(
            query=request.query,
            response=response_text,
            data_analyzed=data,
            insights=insights,
            query_type=intent["type"],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error handling smart query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@router.get("/smart-query/examples")
def get_query_examples():
    """Get example queries that work well with smart query handling"""
    return {
        "recent_activity_queries": [
            "Who clicked recently?",
            "Show me recent click activity",
            "Who clicked in the last 24 hours?",
            "What users clicked today?",
            "Recent phishing clicks"
        ],
        "user_identification_queries": [
            "Which users are clicking on phishing emails?",
            "Who are the high-risk users?",
            "Show me users who clicked multiple times",
            "Which employees fell for phishing?",
            "List users who need more training"
        ],
        "trend_analysis_queries": [
            "What are the click trends this week?",
            "Show me daily click patterns",
            "When do users click most often?",
            "What's the peak hour for clicks?",
            "How has activity changed over time?"
        ],
        "statistics_queries": [
            "How many users clicked this week?",
            "Total clicks today",
            "Click statistics for this month",
            "Overall activity summary",
            "User engagement metrics"
        ]
    }

@router.get("/smart-query/health")
def get_smart_query_health():
    """Health check for smart query system"""
    return {
        "status": "operational",
        "llm_available": LLM_AVAILABLE,
        "data_fetcher_ready": True,
        "click_logs_exist": smart_analyzer.data_fetcher.click_logs_file.exists(),
        "analyzer_ready": True,
        "features": {
            "real_time_data_fetching": True,
            "contextual_llm_responses": LLM_AVAILABLE,
            "fallback_responses": True,
            "query_intent_analysis": True
        }
    }
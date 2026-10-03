from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

class ForecastRequest(BaseModel):
    forecast_days: Optional[int] = 30
    include_trend: Optional[bool] = True
    include_seasonality: Optional[bool] = True
    confidence_interval: Optional[float] = 0.8

class ForecastResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    forecast_data: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    seasonal_patterns: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    model_performance: Dict[str, Any]
    generated_at: str

class ClickForecastingEngine:
    """Prophet-based forecasting engine for phishing click trends"""
    
    def __init__(self):
        self.model = None
        self.forecast = None
        self.historical_data = None
        self.last_training = None
        
    def load_data_pandas(self) -> pd.DataFrame:
        """Load data using same approach as analytics module"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        log_file = os.path.join(data_dir, "click_logs.csv")
        
        if not os.path.exists(log_file):
            # Create sample data for demonstration
            return self._create_sample_data_pandas()
        
        try:
            df = pd.read_csv(log_file)
            if len(df) == 0:
                return self._create_sample_data_pandas()
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Add derived columns like analytics module
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()
            df['is_weekend'] = df['timestamp'].dt.weekday >= 5
            df['time_of_day'] = pd.cut(df['hour'], 
                                     bins=[0, 6, 12, 18, 24], 
                                     labels=['Night', 'Morning', 'Afternoon', 'Evening'],
                                     include_lowest=True)
            
            # Risk scoring based on user behavior (same as analytics)
            user_click_counts = df['user_email'].value_counts()
            df['user_risk_score'] = df['user_email'].map(
                lambda x: min(user_click_counts[x] * 10, 100)
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data with Pandas: {e}")
            return self._create_sample_data_pandas()
    
    def _create_sample_data_pandas(self) -> pd.DataFrame:
        """Create sample data for demonstration purposes - same as analytics module"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='H')
        
        sample_data = []
        users = [f"user{i}@company.com" for i in range(1, 21)]
        
        for date in dates:
            # Simulate realistic click patterns
            if np.random.random() < 0.1:  # 10% chance of clicks per hour
                num_clicks = np.random.poisson(2)
                for _ in range(num_clicks):
                    sample_data.append({
                        'timestamp': date + timedelta(minutes=np.random.randint(0, 60)),
                        'user_email': np.random.choice(users),
                        'action_id': f"phish-{np.random.randint(1000, 9999)}",
                        'ip_address': f"192.168.1.{np.random.randint(1, 255)}"
                    })
        
        df = pd.DataFrame(sample_data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # Add the same derived columns
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()
            df['is_weekend'] = df['timestamp'].dt.weekday >= 5
            df['time_of_day'] = pd.cut(df['hour'], 
                                     bins=[0, 6, 12, 18, 24], 
                                     labels=['Night', 'Morning', 'Afternoon', 'Evening'],
                                     include_lowest=True)
            
            # Risk scoring
            user_click_counts = df['user_email'].value_counts()
            df['user_risk_score'] = df['user_email'].map(
                lambda x: min(user_click_counts[x] * 10, 100)
            )
            
        logger.info(f"Created sample data with {len(df)} records for forecasting")
        return df
    
    def prepare_prophet_data(self, granularity='daily') -> pd.DataFrame:
        """Prepare data for Prophet model"""
        df = self.load_data_pandas()
        
        if len(df) == 0:
            logger.warning("No data available for Prophet")
            return pd.DataFrame(columns=['ds', 'y'])
        
        # Aggregate clicks by day for Prophet
        if granularity == 'daily':
            daily_clicks = df.groupby(df['timestamp'].dt.date).size().reset_index()
            daily_clicks.columns = ['ds', 'y']
            daily_clicks['ds'] = pd.to_datetime(daily_clicks['ds'])
            prophet_data = daily_clicks
        else:  # hourly
            hourly_clicks = df.groupby([
                df['timestamp'].dt.date,
                df['timestamp'].dt.hour
            ]).size().reset_index()
            hourly_clicks.columns = ['date', 'hour', 'y']
            hourly_clicks['ds'] = pd.to_datetime(
                hourly_clicks['date'].astype(str) + ' ' + 
                hourly_clicks['hour'].astype(str) + ':00:00'
            )
            prophet_data = hourly_clicks[['ds', 'y']]
        
        # Store both raw and aggregated data
        self.historical_data = {
            'daily': daily_clicks if granularity == 'daily' else df.groupby(df['timestamp'].dt.date).size().reset_index(),
            'hourly': hourly_clicks[['ds', 'y']] if granularity == 'hourly' else pd.DataFrame(),
            'raw': df
        }
        
        # Add holiday effects
        prophet_data = self.add_holiday_effects(prophet_data)
        
        logger.info(f"Prepared {len(prophet_data)} data points for Prophet forecasting")
        return prophet_data
    
    def add_holiday_effects(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add holiday and special event indicators"""
        if len(df) == 0:
            return df
            
        df = df.copy()
        
        # Add weekend indicator
        df['is_weekend'] = df['ds'].dt.dayofweek.isin([5, 6]).astype(int)
        
        # Add month indicator for seasonal effects
        df['month'] = df['ds'].dt.month
        
        # Add business hours indicator if using hourly data
        if df['ds'].dt.hour.nunique() > 1:
            df['is_business_hours'] = df['ds'].dt.hour.between(9, 17).astype(int)
        
        return df
    
    def train_model(self, granularity='daily', **kwargs) -> Dict[str, Any]:
        """Train Prophet model on historical data"""
        try:
            df = self.prepare_prophet_data(granularity)
            
            if len(df) < 2:
                raise ValueError("Insufficient data points for training Prophet model")
            
            # Configure Prophet model
            model_params = {
                'changepoint_prior_scale': kwargs.get('changepoint_prior_scale', 0.05),
                'seasonality_prior_scale': kwargs.get('seasonality_prior_scale', 10),
                'holidays_prior_scale': kwargs.get('holidays_prior_scale', 10),
                'daily_seasonality': granularity == 'hourly',
                'weekly_seasonality': True,
                'yearly_seasonality': len(df) > 365,
                'interval_width': kwargs.get('confidence_interval', 0.8)
            }
            
            self.model = Prophet(**model_params)
            
            # Add custom seasonalities
            if granularity == 'hourly':
                self.model.add_seasonality(name='hourly', period=24, fourier_order=8)
            
            # Add regressors if available
            if 'is_weekend' in df.columns:
                self.model.add_regressor('is_weekend')
            if 'is_business_hours' in df.columns:
                self.model.add_regressor('is_business_hours')
            
            # Fit model
            self.model.fit(df)
            self.last_training = datetime.utcnow()
            
            # Calculate model performance on historical data
            performance = self.calculate_model_performance(df)
            
            logger.info(f"Prophet model trained with {len(df)} data points")
            
            return {
                'training_data_points': len(df),
                'model_parameters': model_params,
                'performance_metrics': performance,
                'training_time': self.last_training.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error training Prophet model: {e}")
            raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    def calculate_model_performance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate model performance metrics"""
        try:
            # Make predictions on training data
            predictions = self.model.predict(df)
            
            # Calculate metrics
            mae = np.mean(np.abs(predictions['yhat'] - df['y']))
            mape = np.mean(np.abs((df['y'] - predictions['yhat']) / np.maximum(df['y'], 1))) * 100
            rmse = np.sqrt(np.mean((predictions['yhat'] - df['y']) ** 2))
            
            return {
                'mae': float(mae),
                'mape': float(mape),
                'rmse': float(rmse),
                'r_squared': float(np.corrcoef(df['y'], predictions['yhat'])[0, 1] ** 2) if len(df) > 1 else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return {'error': str(e)}
    
    def generate_forecast(self, forecast_days: int = 30) -> pd.DataFrame:
        """Generate forecast for specified number of days"""
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        # Create future dataframe
        future = self.model.make_future_dataframe(periods=forecast_days)
        
        # Add regressors for future periods
        if 'is_weekend' in self.model.extra_regressors:
            future['is_weekend'] = future['ds'].dt.dayofweek.isin([5, 6]).astype(int)
        if 'is_business_hours' in self.model.extra_regressors:
            future['is_business_hours'] = future['ds'].dt.hour.between(9, 17).astype(int)
        
        # Generate forecast
        forecast = self.model.predict(future)
        self.forecast = forecast
        
        return forecast
    
    def analyze_trends(self) -> Dict[str, Any]:
        """Analyze trends from the forecast"""
        if self.forecast is None:
            return {"error": "No forecast available"}
        
        forecast = self.forecast
        if self.historical_data is None or len(self.historical_data['raw']) == 0:
            return {"error": "No historical data available"}
            
        historical_data = self.historical_data['raw']
        
        # Get current trend
        recent_trend = forecast['trend'].tail(30).mean()
        historical_avg = len(historical_data) / max(1, len(self.historical_data.get('daily', [])))
        
        # Seasonal patterns
        seasonal_analysis = {
            'weekly_pattern': self.analyze_weekly_seasonality(),
            'daily_pattern': self.analyze_daily_seasonality() if 'hourly' in self.historical_data else None
        }
        
        # Future predictions
        historical_max_date = historical_data['timestamp'].max() if len(historical_data) > 0 else datetime.now() - timedelta(days=1)
        future_forecast = forecast[forecast['ds'] > historical_max_date]
        
        return {
            'current_trend': 'increasing' if recent_trend > historical_avg else 'decreasing',
            'trend_strength': float(abs(recent_trend - historical_avg) / max(historical_avg, 1) * 100),
            'seasonal_patterns': seasonal_analysis,
            'predicted_total_clicks': float(future_forecast['yhat'].sum()) if len(future_forecast) > 0 else 0.0,
            'peak_risk_days': future_forecast.nlargest(5, 'yhat')[['ds', 'yhat']].to_dict('records') if len(future_forecast) > 0 else [],
            'confidence_bounds': {
                'upper': float(future_forecast['yhat_upper'].mean()) if len(future_forecast) > 0 else 0.0,
                'lower': float(future_forecast['yhat_lower'].mean()) if len(future_forecast) > 0 else 0.0
            }
        }
    
    def analyze_weekly_seasonality(self) -> Dict[str, Any]:
        """Analyze weekly seasonality patterns"""
        if self.historical_data is None or len(self.historical_data['raw']) == 0:
            return {
                'highest_risk_day': 'Monday',
                'lowest_risk_day': 'Sunday',
                'pattern': {day: 0 for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
            }
        
        df = self.historical_data['raw']
        weekly_pattern = df.groupby(df['day_of_week']).size()
        
        if len(weekly_pattern) == 0:
            return {
                'highest_risk_day': 'Monday',
                'lowest_risk_day': 'Sunday',
                'pattern': {day: 0 for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
            }
        
        return {
            'highest_risk_day': weekly_pattern.idxmax(),
            'lowest_risk_day': weekly_pattern.idxmin(),
            'pattern': weekly_pattern.to_dict()
        }
    
    def analyze_daily_seasonality(self) -> Dict[str, Any]:
        """Analyze daily (hourly) seasonality patterns"""
        if self.historical_data is None or len(self.historical_data['raw']) == 0:
            return {
                'peak_hour': 14,
                'lowest_hour': 3,
                'business_hours_risk': 5.0,
                'after_hours_risk': 2.0,
                'hourly_pattern': {hour: 0 for hour in range(24)}
            }
        
        df = self.historical_data['raw']
        hourly_pattern = df.groupby(df['hour']).size()
        
        if len(hourly_pattern) == 0:
            return {
                'peak_hour': 14,
                'lowest_hour': 3,
                'business_hours_risk': 5.0,
                'after_hours_risk': 2.0,
                'hourly_pattern': {hour: 0 for hour in range(24)}
            }
        
        # Calculate business hours vs after hours risk
        business_hours = hourly_pattern.reindex(range(9, 17), fill_value=0)
        after_hours_indices = list(range(0, 9)) + list(range(17, 24))
        after_hours = hourly_pattern.reindex(after_hours_indices, fill_value=0)
        
        return {
            'peak_hour': int(hourly_pattern.idxmax()),
            'lowest_hour': int(hourly_pattern.idxmin()),
            'business_hours_risk': float(business_hours.mean()) if len(business_hours) > 0 else 0.0,
            'after_hours_risk': float(after_hours.mean()) if len(after_hours) > 0 else 0.0,
            'hourly_pattern': {int(k): int(v) for k, v in hourly_pattern.to_dict().items()}
        }
    
    def generate_recommendations(self, trend_analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on forecast"""
        recommendations = []
        
        if trend_analysis.get('current_trend') == 'increasing':
            recommendations.append("Click trend is increasing - consider intensifying security training")
        
        seasonal = trend_analysis.get('seasonal_patterns', {})
        if seasonal.get('weekly_pattern'):
            highest_day = seasonal['weekly_pattern'].get('highest_risk_day')
            if highest_day:
                recommendations.append(f"Schedule additional training before {highest_day}s (highest risk day)")
        
        if seasonal.get('daily_pattern'):
            peak_hour = seasonal['daily_pattern'].get('peak_hour')
            if peak_hour:
                recommendations.append(f"Monitor closely around {peak_hour}:00 (peak risk hour)")
        
        predicted_total = trend_analysis.get('predicted_total_clicks', 0)
        if predicted_total > 50:  # Arbitrary threshold
            recommendations.append("High click volume predicted - prepare incident response procedures")
        
        confidence_bounds = trend_analysis.get('confidence_bounds', {})
        if confidence_bounds.get('upper', 0) - confidence_bounds.get('lower', 0) > 10:
            recommendations.append("High uncertainty in predictions - collect more training data")
        
        if not recommendations:
            recommendations.append("Continue monitoring click patterns and user behavior")
        
        return recommendations

# Initialize forecasting engine
forecasting_engine = ClickForecastingEngine()

@router.post("/generate", response_model=ForecastResponse)
async def generate_click_forecast(request: ForecastRequest):
    """Generate click trend forecast using Prophet"""
    try:
        # Train model if not already trained or if data is stale
        training_info = forecasting_engine.train_model(
            confidence_interval=request.confidence_interval
        )
        
        # Generate forecast
        forecast_df = forecasting_engine.generate_forecast(request.forecast_days)
        
        # Analyze trends
        trend_analysis = forecasting_engine.analyze_trends()
        
        # Generate recommendations
        recommendations = forecasting_engine.generate_recommendations(trend_analysis)
        
        # Prepare forecast data for response
        historical_data = forecasting_engine.historical_data['raw']
        historical_max_date = historical_data['timestamp'].max() if len(historical_data) > 0 else datetime.now() - timedelta(days=1)
        future_data = forecast_df[forecast_df['ds'] > historical_max_date]
        forecast_data = []
        
        for _, row in future_data.iterrows():
            forecast_data.append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'predicted_clicks': float(row['yhat']),
                'lower_bound': float(row['yhat_lower']),
                'upper_bound': float(row['yhat_upper']),
                'trend': float(row['trend']),
                'weekly_seasonality': float(row.get('weekly', 0)),
                'daily_seasonality': float(row.get('daily', 0))
            })
        
        return ForecastResponse(
            forecast_data=forecast_data,
            trend_analysis=trend_analysis,
            seasonal_patterns=trend_analysis.get('seasonal_patterns', {}),
            risk_assessment={
                'overall_risk': 'high' if trend_analysis.get('predicted_total_clicks', 0) > 100 else 'medium',
                'peak_risk_days': trend_analysis.get('peak_risk_days', []),
                'confidence_level': request.confidence_interval
            },
            recommendations=recommendations,
            model_performance=training_info.get('performance_metrics', {}),
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")

@router.get("/model-status")
async def get_model_status():
    """Get current status of the forecasting model"""
    return {
        'model_trained': forecasting_engine.model is not None,
        'last_training': forecasting_engine.last_training.isoformat() if forecasting_engine.last_training else None,
        'forecast_available': forecasting_engine.forecast is not None,
        'data_points': len(forecasting_engine.historical_data['raw']) if forecasting_engine.historical_data else 0
    }

@router.post("/retrain")
async def retrain_model():
    """Manually retrain the forecasting model"""
    try:
        training_info = forecasting_engine.train_model()
        return {
            'message': 'Model retrained successfully',
            'training_info': training_info
        }
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")

@router.get("/visualization")
async def get_forecast_visualization():
    """Get forecast visualization data for frontend charts"""
    try:
        if forecasting_engine.forecast is None:
            raise HTTPException(status_code=400, detail="No forecast available. Generate forecast first.")
        
        forecast = forecasting_engine.forecast
        historical = forecasting_engine.historical_data['raw']
        
        # Prepare chart data
        chart_data = {
            'historical': [{'ds': row['timestamp'].isoformat(), 'y': 1} for _, row in historical.iterrows()],
            'forecast': forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict('records'),
            'components': {
                'trend': forecast[['ds', 'trend']].to_dict('records'),
                'weekly': forecast[['ds', 'weekly']].to_dict('records') if 'weekly' in forecast.columns else [],
                'daily': forecast[['ds', 'daily']].to_dict('records') if 'daily' in forecast.columns else []
            }
        }
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating visualization data: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization generation failed: {str(e)}")
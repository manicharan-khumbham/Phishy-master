from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from enum import Enum
import json

router = APIRouter()
logger = logging.getLogger(__name__)

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif pd.isna(obj):
        return None
    else:
        return obj

class AnalyticsEngine(Enum):
    PANDAS = "pandas"
    POLARS = "polars"

class TimeRange(Enum):
    HOUR = "1H"
    DAY = "1D"
    WEEK = "1W"
    MONTH = "1M"

class AnalyticsRequest(BaseModel):
    engine: Optional[AnalyticsEngine] = AnalyticsEngine.PANDAS
    time_range: Optional[str] = None  # "24h", "7d", "30d", "90d"
    group_by: Optional[str] = None  # "user", "day", "hour", "ip"
    metrics: Optional[List[str]] = ["clicks", "unique_users", "risk_score"]
    filters: Optional[Dict[str, Any]] = {}

class AnalyticsResponse(BaseModel):
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]
    insights: List[str]
    processing_time: float
    engine_used: str
    generated_at: str

class AdvancedAnalytics:
    """Advanced analytics engine supporting both Pandas and Polars"""
    
    def __init__(self):
        self.data_cache = {}
        self.cache_expiry = timedelta(minutes=5)
        self.last_cache_update = None
    
    def load_data_pandas(self) -> pd.DataFrame:
        """Load data directly from SQLite Database using Pandas"""
        try:
            from database import get_db_connection
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT timestamp, user_email, action_id, ip_address, user_agent, referer FROM click_logs", conn)
            conn.close()
            if df.empty:
                return self._create_sample_data_pandas()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Add derived columns
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()
            df['is_weekend'] = df['timestamp'].dt.weekday >= 5
            df['time_of_day'] = pd.cut(df['hour'], 
                                     bins=[0, 6, 12, 18, 24], 
                                     labels=['Night', 'Morning', 'Afternoon', 'Evening'],
                                     include_lowest=True)
            
            # Risk scoring based on user behavior
            user_click_counts = df['user_email'].value_counts()
            df['user_risk_score'] = df['user_email'].map(
                lambda x: min(user_click_counts[x] * 10, 100)
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data with Pandas: {e}")
            return self._create_sample_data_pandas()
    
    def load_data_polars(self) -> pl.DataFrame:
        """Load data using Polars"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        log_file = os.path.join(data_dir, "click_logs.csv")
        
        if not os.path.exists(log_file):
            return self._create_sample_data_polars()
        
        try:
            df = pl.read_csv(log_file)
            
            # Convert timestamp and add derived columns
            df = df.with_columns([
                pl.col('timestamp').str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S.%f").alias('timestamp'),
            ]).with_columns([
                pl.col('timestamp').dt.date().alias('date'),
                pl.col('timestamp').dt.hour().alias('hour'),
                pl.col('timestamp').dt.strftime('%A').alias('day_of_week'),
                (pl.col('timestamp').dt.weekday() >= 6).alias('is_weekend'),
                pl.when(pl.col('timestamp').dt.hour() < 6).then(pl.lit('Night'))
                  .when(pl.col('timestamp').dt.hour() < 12).then(pl.lit('Morning'))
                  .when(pl.col('timestamp').dt.hour() < 18).then(pl.lit('Afternoon'))
                  .otherwise(pl.lit('Evening')).alias('time_of_day')
            ])
            
            # Add risk scoring
            user_counts = df.group_by('user_email').agg(pl.count().alias('click_count'))
            df = df.join(user_counts, on='user_email').with_columns([
                (pl.col('click_count') * 10).clip(0, 100).alias('user_risk_score')
            ])
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data with Polars: {e}")
            return self._create_sample_data_polars()
    
    def _create_sample_data_pandas(self) -> pd.DataFrame:
        """Create sample data for demonstration purposes"""
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
        return df
    
    def _create_sample_data_polars(self) -> pl.DataFrame:
        """Create sample data using Polars"""
        pandas_df = self._create_sample_data_pandas()
        if pandas_df.empty:
            return pl.DataFrame()
        return pl.from_pandas(pandas_df)
    
    def apply_time_filter(self, df: Union[pd.DataFrame, pl.DataFrame], time_range: str) -> Union[pd.DataFrame, pl.DataFrame]:
        """Apply time range filter to dataframe"""
        if time_range is None:
            return df
        
        now = datetime.utcnow()
        time_mapping = {
            '1h': timedelta(hours=1),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
            '90d': timedelta(days=90)
        }
        
        delta = time_mapping.get(time_range, timedelta(days=7))
        cutoff = now - delta
        
        if isinstance(df, pd.DataFrame):
            return df[df['timestamp'] >= cutoff]
        else:  # Polars
            return df.filter(pl.col('timestamp') >= cutoff)
    
    def analyze_with_pandas(self, request: AnalyticsRequest) -> Dict[str, Any]:
        """Perform analysis using Pandas"""
        start_time = datetime.utcnow()
        
        # Load and filter data
        df = self.load_data_pandas()
        if request.time_range:
            df = self.apply_time_filter(df, request.time_range)
        
        # Apply additional filters
        for field, value in (request.filters or {}).items():
            if field in df.columns:
                if isinstance(value, list):
                    df = df[df[field].isin(value)]
                else:
                    df = df[df[field] == value]
        
        results = []
        summary = {}
        
        # Group by analysis
        if request.group_by:
            group_col = self._map_group_by_column(request.group_by)
            if group_col in df.columns:
                grouped = df.groupby(group_col).agg({
                    'user_email': ['count', 'nunique'],
                    'user_risk_score': 'mean',
                    'ip_address': 'nunique'
                }).round(2)
                
                grouped.columns = ['total_clicks', 'unique_users', 'avg_risk_score', 'unique_ips']
                grouped = grouped.reset_index()
                
                # Convert to dict and fix numpy types
                results = convert_numpy_types(grouped.to_dict('records'))
        
        # Calculate summary statistics
        if not df.empty:
            summary = {
                'total_records': int(len(df)),
                'unique_users': int(df['user_email'].nunique()),
                'unique_ips': int(df['ip_address'].nunique()),
                'date_range': {
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat()
                },
                'avg_risk_score': float(df['user_risk_score'].mean()),
                'high_risk_users': int(len(df[df['user_risk_score'] > 50])),
                'weekend_clicks': int(len(df[df['is_weekend']])),
                'business_hours_clicks': int(len(df[df['hour'].between(9, 17)])),
                'top_users': convert_numpy_types(df['user_email'].value_counts().head(5).to_dict()),
                'hourly_distribution': convert_numpy_types(df.groupby('hour').size().to_dict()),
                'daily_distribution': convert_numpy_types(df.groupby('day_of_week').size().to_dict())
            }
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            'data': results,
            'summary': summary,
            'processing_time': processing_time,
            'engine_used': 'pandas'
        }
    
    def analyze_with_polars(self, request: AnalyticsRequest) -> Dict[str, Any]:
        """Perform analysis using Polars"""
        start_time = datetime.utcnow()
        
        # Load and filter data
        df = self.load_data_polars()
        if request.time_range:
            df = self.apply_time_filter(df, request.time_range)
        
        # Apply additional filters
        for field, value in (request.filters or {}).items():
            if field in df.columns:
                if isinstance(value, list):
                    df = df.filter(pl.col(field).is_in(value))
                else:
                    df = df.filter(pl.col(field) == value)
        
        results = []
        summary = {}
        
        # Group by analysis
        if request.group_by:
            group_col = self._map_group_by_column(request.group_by)
            if group_col in df.columns:
                grouped = df.group_by(group_col).agg([
                    pl.count().alias('total_clicks'),
                    pl.col('user_email').n_unique().alias('unique_users'),
                    pl.col('user_risk_score').mean().alias('avg_risk_score'),
                    pl.col('ip_address').n_unique().alias('unique_ips')
                ]).sort(group_col)
                
                results = grouped.to_dicts()
        
        # Calculate summary statistics
        if df.height > 0:
            summary_stats = df.select([
                pl.count().alias('total_records'),
                pl.col('user_email').n_unique().alias('unique_users'),
                pl.col('ip_address').n_unique().alias('unique_ips'),
                pl.col('timestamp').min().alias('start_date'),
                pl.col('timestamp').max().alias('end_date'),
                pl.col('user_risk_score').mean().alias('avg_risk_score'),
                (pl.col('user_risk_score') > 50).sum().alias('high_risk_users'),
                pl.col('is_weekend').sum().alias('weekend_clicks'),
                (pl.col('hour').is_between(9, 17)).sum().alias('business_hours_clicks')
            ]).to_dicts()[0]
            
            # Get top users
            top_users = df.group_by('user_email').agg(
                pl.count().alias('clicks')
            ).sort('clicks', descending=True).limit(5).to_dicts()
            
            # Get distributions
            hourly_dist = df.group_by('hour').agg(pl.count().alias('count')).sort('hour').to_dicts()
            daily_dist = df.group_by('day_of_week').agg(pl.count().alias('count')).to_dicts()
            
            summary = {
                'total_records': int(summary_stats['total_records']),
                'unique_users': int(summary_stats['unique_users']),
                'unique_ips': int(summary_stats['unique_ips']),
                'date_range': {
                    'start': summary_stats['start_date'].isoformat() if summary_stats['start_date'] else None,
                    'end': summary_stats['end_date'].isoformat() if summary_stats['end_date'] else None
                },
                'avg_risk_score': float(summary_stats['avg_risk_score']) if summary_stats['avg_risk_score'] else 0.0,
                'high_risk_users': int(summary_stats['high_risk_users']),
                'weekend_clicks': int(summary_stats['weekend_clicks']),
                'business_hours_clicks': int(summary_stats['business_hours_clicks']),
                'top_users': {user['user_email']: int(user['clicks']) for user in top_users},
                'hourly_distribution': {str(item['hour']): int(item['count']) for item in hourly_dist},
                'daily_distribution': {item['day_of_week']: int(item['count']) for item in daily_dist}
            }
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            'data': results,
            'summary': summary,
            'processing_time': processing_time,
            'engine_used': 'polars'
        }
    
    def _map_group_by_column(self, group_by: str) -> str:
        """Map group_by parameter to actual column name"""
        mapping = {
            'user': 'user_email',
            'day': 'date',
            'hour': 'hour',
            'ip': 'ip_address',
            'weekday': 'day_of_week',
            'time_of_day': 'time_of_day'
        }
        return mapping.get(group_by, group_by)
    
    def generate_insights(self, summary: Dict[str, Any], data: List[Dict[str, Any]]) -> List[str]:
        """Generate analytical insights from the data"""
        insights = []
        
        if summary:
            # Risk-based insights
            avg_risk = summary.get('avg_risk_score', 0)
            if avg_risk > 30:
                insights.append(f"High average risk score ({avg_risk:.1f}/100) indicates need for targeted training")
            
            # User behavior insights
            total_clicks = summary.get('total_records', 0)
            unique_users = summary.get('unique_users', 1)
            clicks_per_user = total_clicks / unique_users if unique_users > 0 else 0
            
            if clicks_per_user > 2:
                insights.append(f"Average {clicks_per_user:.1f} clicks per user suggests repeat offenders")
            
            # Time-based insights
            weekend_ratio = summary.get('weekend_clicks', 0) / total_clicks if total_clicks > 0 else 0
            if weekend_ratio > 0.3:
                insights.append("High weekend activity may indicate personal device usage")
            
            business_ratio = summary.get('business_hours_clicks', 0) / total_clicks if total_clicks > 0 else 0
            if business_ratio < 0.5:
                insights.append("Many clicks outside business hours - consider off-hours monitoring")
            
            # Distribution insights
            hourly_dist = summary.get('hourly_distribution', {})
            if hourly_dist:
                peak_hour = max(hourly_dist, key=hourly_dist.get)
                insights.append(f"Peak activity at {peak_hour}:00 - schedule training accordingly")
            
            daily_dist = summary.get('daily_distribution', {})
            if daily_dist:
                peak_day = max(daily_dist, key=daily_dist.get)
                insights.append(f"{peak_day} shows highest click activity")
            
            # IP analysis
            unique_ips = summary.get('unique_ips', 0)
            if unique_ips < unique_users * 0.8:
                insights.append("Multiple users from same IPs - possible shared workstations")
        
        return insights
    
    def perform_comparative_analysis(self, engine1: str, engine2: str, request: AnalyticsRequest) -> Dict[str, Any]:
        """Compare performance between Pandas and Polars"""
        results = {}
        
        # Test with Pandas
        pandas_request = request.model_copy()
        pandas_request.engine = AnalyticsEngine.PANDAS
        pandas_result = self.analyze_with_pandas(pandas_request)
        
        # Test with Polars
        polars_request = request.model_copy()
        polars_request.engine = AnalyticsEngine.POLARS
        polars_result = self.analyze_with_polars(polars_request)
        
        return {
            'pandas': {
                'processing_time': pandas_result['processing_time'],
                'data_count': len(pandas_result['data']),
                'summary_keys': list(pandas_result['summary'].keys())
            },
            'polars': {
                'processing_time': polars_result['processing_time'],
                'data_count': len(polars_result['data']),
                'summary_keys': list(polars_result['summary'].keys())
            },
            'performance_improvement': {
                'speed_ratio': pandas_result['processing_time'] / polars_result['processing_time'] if polars_result['processing_time'] > 0 else 0,
                'faster_engine': 'polars' if polars_result['processing_time'] < pandas_result['processing_time'] else 'pandas'
            }
        }

# Initialize analytics engine
analytics_engine = AdvancedAnalytics()

@router.post("/analyze", response_model=AnalyticsResponse)
async def perform_analytics(request: AnalyticsRequest):
    """Perform advanced analytics on click data"""
    try:
        if request.engine == AnalyticsEngine.PANDAS:
            result = analytics_engine.analyze_with_pandas(request)
        else:
            result = analytics_engine.analyze_with_polars(request)
        
        insights = analytics_engine.generate_insights(result['summary'], result['data'])
        
        return AnalyticsResponse(
            data=result['data'],
            summary=result['summary'],
            insights=insights,
            processing_time=result['processing_time'],
            engine_used=result['engine_used'],
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@router.get("/user-profile/{user_email}")
async def get_user_profile(user_email: str, engine: AnalyticsEngine = AnalyticsEngine.PANDAS):
    """Get detailed profile for a specific user"""
    try:
        if engine == AnalyticsEngine.PANDAS:
            df = analytics_engine.load_data_pandas()
            user_data = df[df['user_email'] == user_email]
            
            if user_data.empty:
                return {"message": f"No data found for user {user_email}"}
            
            profile = {
                'user_email': user_email,
                'total_clicks': int(len(user_data)),
                'first_click': user_data['timestamp'].min().isoformat(),
                'last_click': user_data['timestamp'].max().isoformat(),
                'risk_score': float(user_data['user_risk_score'].iloc[0]),
                'click_patterns': {
                    'by_hour': convert_numpy_types(user_data.groupby('hour').size().to_dict()),
                    'by_day': convert_numpy_types(user_data.groupby('day_of_week').size().to_dict()),
                    'by_time_of_day': convert_numpy_types(user_data.groupby('time_of_day').size().to_dict())
                },
                'unique_ips': int(user_data['ip_address'].nunique()),
                'ip_addresses': user_data['ip_address'].unique().tolist(),
                'recent_activity': convert_numpy_types(user_data.tail(10)[['timestamp', 'action_id', 'ip_address']].to_dict('records'))
            }
        else:
            df = analytics_engine.load_data_polars()
            user_data = df.filter(pl.col('user_email') == user_email)
            
            if user_data.height == 0:
                return {"message": f"No data found for user {user_email}"}
            
            user_stats = user_data.select([
                pl.count().alias('total_clicks'),
                pl.col('timestamp').min().alias('first_click'),
                pl.col('timestamp').max().alias('last_click'),
                pl.col('user_risk_score').first().alias('risk_score'),
                pl.col('ip_address').n_unique().alias('unique_ips')
            ]).to_dicts()[0]
            
            profile = {
                'user_email': user_email,
                'total_clicks': int(user_stats['total_clicks']),
                'first_click': user_stats['first_click'].isoformat(),
                'last_click': user_stats['last_click'].isoformat(),
                'risk_score': float(user_stats['risk_score']),
                'unique_ips': int(user_stats['unique_ips']),
                'ip_addresses': user_data.select('ip_address').unique().to_series().to_list(),
                'recent_activity': user_data.tail(10).select(['timestamp', 'action_id', 'ip_address']).to_dicts()
            }
        
        return profile
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=f"User profile error: {str(e)}")

@router.get("/performance-comparison")
async def compare_engine_performance(
    time_range: Optional[str] = Query(None, description="Time range filter"),
    group_by: Optional[str] = Query(None, description="Group by field")
):
    """Compare performance between Pandas and Polars"""
    try:
        request = AnalyticsRequest(
            time_range=time_range,
            group_by=group_by,
            metrics=["clicks", "unique_users"]
        )
        
        comparison = analytics_engine.perform_comparative_analysis("pandas", "polars", request)
        return comparison
        
    except Exception as e:
        logger.error(f"Error in performance comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")

@router.get("/risk-assessment")
async def generate_risk_assessment(engine: AnalyticsEngine = AnalyticsEngine.POLARS):
    """Generate comprehensive risk assessment"""
    try:
        # Load data with chosen engine
        if engine == AnalyticsEngine.PANDAS:
            df = analytics_engine.load_data_pandas()
            
            high_risk_users = df[df['user_risk_score'] > 50]['user_email'].unique().tolist()
            repeat_offenders = df['user_email'].value_counts()
            repeat_offenders = convert_numpy_types(repeat_offenders[repeat_offenders > 3].to_dict())
            
            ip_analysis = df.groupby('ip_address').agg({
                'user_email': 'nunique',
                'timestamp': 'count'
            }).rename(columns={'user_email': 'unique_users', 'timestamp': 'total_clicks'})
            suspicious_ips = convert_numpy_types(ip_analysis[ip_analysis['unique_users'] > 5].to_dict('index'))
            
        else:
            df = analytics_engine.load_data_polars()
            
            high_risk_users = df.filter(pl.col('user_risk_score') > 50).select('user_email').unique().to_series().to_list()
            
            repeat_data = df.group_by('user_email').agg(pl.count().alias('clicks')).filter(pl.col('clicks') > 3)
            repeat_offenders = {row['user_email']: int(row['clicks']) for row in repeat_data.to_dicts()}
            
            ip_data = df.group_by('ip_address').agg([
                pl.col('user_email').n_unique().alias('unique_users'),
                pl.count().alias('total_clicks')
            ]).filter(pl.col('unique_users') > 5)
            suspicious_ips = {row['ip_address']: {'unique_users': int(row['unique_users']), 'total_clicks': int(row['total_clicks'])} for row in ip_data.to_dicts()}
        
        assessment = {
            'overall_risk_level': 'HIGH' if len(high_risk_users) > 5 else 'MEDIUM' if len(high_risk_users) > 2 else 'LOW',
            'high_risk_users': high_risk_users,
            'repeat_offenders': repeat_offenders,
            'suspicious_ips': suspicious_ips,
            'recommendations': [
                f"Immediate training required for {len(high_risk_users)} high-risk users",
                f"Monitor {len(repeat_offenders)} repeat offenders closely",
                f"Investigate {len(suspicious_ips)} suspicious IP addresses",
                "Consider implementing additional security controls"
            ],
            'generated_with': engine.value,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return assessment
        
    except Exception as e:
        logger.error(f"Error generating risk assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Risk assessment error: {str(e)}")

@router.get("/trends")
async def analyze_trends(
    granularity: TimeRange = TimeRange.DAY,
    engine: AnalyticsEngine = AnalyticsEngine.POLARS
):
    """Analyze trends over time with different granularities"""
    try:
        if engine == AnalyticsEngine.PANDAS:
            df = analytics_engine.load_data_pandas()
            
            # Resample based on granularity
            trend_data = df.set_index('timestamp').resample(granularity.value).agg({
                'user_email': ['count', 'nunique'],
                'user_risk_score': 'mean'
            }).round(2)
            
            trend_data.columns = ['total_clicks', 'unique_users', 'avg_risk_score']
            trend_results = convert_numpy_types(trend_data.reset_index().to_dict('records'))
            
        else:
            df = analytics_engine.load_data_polars()
            
            # Group by time period
            if granularity == TimeRange.HOUR:
                df = df.with_columns(pl.col('timestamp').dt.truncate('1h').alias('period'))
            elif granularity == TimeRange.DAY:
                df = df.with_columns(pl.col('timestamp').dt.truncate('1d').alias('period'))
            elif granularity == TimeRange.WEEK:
                df = df.with_columns(pl.col('timestamp').dt.truncate('1w').alias('period'))
            else:  # MONTH
                df = df.with_columns(pl.col('timestamp').dt.truncate('1mo').alias('period'))
            
            trend_data = df.group_by('period').agg([
                pl.count().alias('total_clicks'),
                pl.col('user_email').n_unique().alias('unique_users'),
                pl.col('user_risk_score').mean().alias('avg_risk_score')
            ]).sort('period')
            
            trend_results = trend_data.to_dicts()
        
        return {
            'trends': trend_results,
            'granularity': granularity.value,
            'engine_used': engine.value,
            'insights': [
                f"Analyzed {len(trend_results)} time periods",
                f"Data aggregated at {granularity.value} intervals"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        raise HTTPException(status_code=500, detail=f"Trend analysis error: {str(e)}")

@router.get("/health")
async def get_analytics_health():
    """Get health status of analytics engine"""
    try:
        pandas_df = analytics_engine.load_data_pandas()
        polars_df = analytics_engine.load_data_polars()
        
        return {
            'status': 'healthy',
            'pandas_data_points': int(len(pandas_df)),
            'polars_data_points': int(polars_df.height),
            'data_consistency': len(pandas_df) == polars_df.height,
            'available_engines': ['pandas', 'polars'],
            'supported_operations': ['analyze', 'user_profile', 'risk_assessment', 'trends', 'performance_comparison']
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
    
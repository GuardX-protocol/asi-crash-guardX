from prophet import Prophet
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class ProphetCrashDetector:
    
    def __init__(self):
        self.models = {}  # Store Prophet models per symbol
    
    def prepare_data(self, price_history, timestamps):
        """Convert to Prophet format: ds (date) and y (value)"""
        df = pd.DataFrame({
            'ds': pd.to_datetime(timestamps),
            'y': price_history
        })
        return df
    
    def predict_crash(self, symbol, price_history, timestamps, periods=10):
        """
        Predict next 'periods' minutes
        NO TRAINING - Prophet auto-fits the model
        """
        try:
            # Need at least 30 data points for Prophet
            if len(price_history) < 30:
                return {
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': 'Insufficient data (need 30+ points)'
                }
            
            # Prepare data for Prophet
            df = self.prepare_data(price_history, timestamps)
            
            # Create Prophet model (NO manual training!)
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=False,
                yearly_seasonality=False,
                changepoint_prior_scale=0.5,  # Flexibility for trend changes
                interval_width=0.95,  # 95% confidence interval
                seasonality_mode='multiplicative'
            )
            
            # Fit model (automatic - takes seconds)
            model.fit(df)
            
            # Create future dataframe for prediction
            future = model.make_future_dataframe(periods=periods, freq='1min')
            
            # Predict (automatic)
            forecast = model.predict(future)
            
            # Get predictions
            current_price = price_history[-1]
            predicted_prices = forecast['yhat'].tail(periods).values
            lower_bound = forecast['yhat_lower'].tail(periods).values
            upper_bound = forecast['yhat_upper'].tail(periods).values
            
            # Detect crash based on predictions
            return self.analyze_crash(
                current_price, 
                predicted_prices,
                lower_bound,
                upper_bound,
                symbol
            )
            
        except Exception as e:
            return {
                'crash_detected': False,
                'crash_probability': 0,
                'error': f'Prophet prediction failed: {str(e)}'
            }
    
    def analyze_crash(self, current_price, predicted, lower, upper, symbol):
        """Analyze if crash is predicted"""
        
        # Calculate predicted drops
        price_changes = ((predicted - current_price) / current_price) * 100
        max_drop = min(price_changes)
        max_drop_index = np.argmin(price_changes)
        
        # Calculate uncertainty (wider intervals = more uncertainty)
        uncertainty = np.mean(upper - lower) / current_price * 100
        
        # Crash detection logic
        downward_count = sum(price_changes < 0)
        trend_strength = downward_count / len(price_changes)
        
        # Calculate crash probability
        magnitude_score = min(abs(max_drop) / 5.0, 1.0) * 50
        trend_score = trend_strength * 30
        confidence_score = (1 - min(uncertainty / 10, 1.0)) * 20
        
        crash_probability = magnitude_score + trend_score + confidence_score
        
        # Additional volatility check
        volatility = np.std(price_changes)
        if volatility > 2.0:  # High volatility
            crash_probability += 10
        
        return {
            'crash_detected': crash_probability > 60,
            'crash_probability': min(crash_probability, 100),
            'predicted_drop': max_drop,
            'crash_horizon_minutes': max_drop_index + 1,
            'predicted_prices': predicted.tolist(),
            'lower_bound': lower.tolist(),
            'upper_bound': upper.tolist(),
            'uncertainty': uncertainty,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'method': 'Facebook Prophet',
            'symbol': symbol,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat()
        }
"""
ARIMA Crash Detector - Auto-tuning, NO MANUAL TRAINING
Automatically finds best (p,d,q) parameters
"""

from statsmodels.tsa.arima.model import ARIMA
from itertools import product
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ARIMACrashDetector:
    """
    ARIMA with auto-tuning - NO MANUAL TRAINING
    Automatically finds best (p,d,q) parameters
    """
    
    def __init__(self):
        self.fitted_models = {}
    
    def auto_arima(self, data, max_p=3, max_d=2, max_q=3):
        """
        Automatically find best ARIMA parameters
        Returns fitted model
        """
        # Define parameter ranges (typical values for crypto)
        p_range = range(0, max_p)
        d_range = range(0, max_d)
        q_range = range(0, max_q)
        
        best_aic = float('inf')
        best_model = None
        best_params = None
        
        # Grid search for best parameters
        for p, d, q in product(p_range, d_range, q_range):
            try:
                model = ARIMA(data, order=(p, d, q))
                fitted = model.fit()
                
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_model = fitted
                    best_params = (p, d, q)
            except:
                continue
        
        return best_model, best_params, best_aic
    
    def predict_crash(self, symbol, price_history, periods=10):
        """
        Predict crash using auto-tuned ARIMA
        """
        try:
            # Need at least 20 data points for ARIMA
            if len(price_history) < 20:
                return {
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': 'Insufficient data (need 20+ points)'
                }
            
            # Convert to numpy array
            data = np.array(price_history)
            
            # Auto-find best ARIMA model
            model, params, aic = self.auto_arima(data)
            
            if model is None:
                return {
                    'crash_detected': False, 
                    'crash_probability': 0,
                    'error': 'Could not fit ARIMA model'
                }
            
            # Forecast future prices
            forecast_result = model.get_forecast(steps=periods)
            predicted_prices = forecast_result.predicted_mean.values
            
            # Get confidence intervals
            conf_int = forecast_result.conf_int()
            lower_bound = conf_int.iloc[:, 0].values
            upper_bound = conf_int.iloc[:, 1].values
            
            current_price = price_history[-1]
            
            # Analyze for crash
            return self.analyze_crash(
                current_price,
                predicted_prices,
                lower_bound,
                upper_bound,
                params,
                aic,
                symbol
            )
            
        except Exception as e:
            return {
                'crash_detected': False,
                'crash_probability': 0,
                'error': f'ARIMA prediction failed: {str(e)}'
            }
    
    def analyze_crash(self, current_price, predicted, lower, upper, params, aic, symbol):
        """Analyze crash probability from ARIMA predictions"""
        
        # Calculate price changes
        price_changes = ((predicted - current_price) / current_price) * 100
        max_drop = min(price_changes)
        max_drop_index = np.argmin(price_changes)
        
        # Calculate prediction confidence
        avg_interval_width = np.mean(upper - lower) / current_price * 100
        confidence = max(0, 100 - avg_interval_width * 2)
        
        # Trend analysis
        downward_trend = sum(price_changes < 0) / len(price_changes)
        
        # Calculate crash probability
        drop_severity = min(abs(max_drop) / 3.0, 1.0) * 40  # Max 40 points
        trend_score = downward_trend * 35  # Max 35 points
        confidence_score = confidence / 100 * 25  # Max 25 points
        
        crash_probability = drop_severity + trend_score + confidence_score
        
        # Model quality bonus (lower AIC = better model)
        if aic < 100:
            crash_probability += 5
        
        return {
            'crash_detected': crash_probability > 65,
            'crash_probability': min(crash_probability, 100),
            'predicted_drop': max_drop,
            'crash_horizon_minutes': max_drop_index + 1,
            'predicted_prices': predicted.tolist(),
            'lower_bound': lower.tolist(),
            'upper_bound': upper.tolist(),
            'confidence': confidence,
            'trend_strength': downward_trend,
            'model_params': params,
            'model_aic': aic,
            'method': 'Auto-ARIMA',
            'symbol': symbol,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat()
        }
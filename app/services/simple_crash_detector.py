"""
Simple Crash Detector - No external dependencies required
Uses basic statistical analysis for crash detection
"""

from datetime import datetime
from typing import List, Dict, Any
import statistics
import math

class SimpleCrashDetector:
    """Simple crash detector using basic statistical methods"""
    
    def __init__(self):
        self.name = "Simple Statistical Crash Detector"
    
    def predict_crash(self, symbol: str, price_history: List[float], timestamps: List[datetime], periods: int = 10) -> Dict[str, Any]:
        """
        Predict crash probability using simple statistical analysis
        """
        try:
            if len(price_history) < 10:
                return {
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': 'Insufficient data (need 10+ points)'
                }
            
            # Use built-in Python functions instead of numpy
            prices = price_history
            current_price = prices[-1]
            
            # Calculate basic statistics
            returns = []
            for i in range(1, len(prices)):
                ret = (prices[i] - prices[i-1]) / prices[i-1] * 100
                returns.append(ret)
            
            if not returns:
                return {'crash_detected': False, 'crash_probability': 0, 'error': 'No returns calculated'}
            
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            mean_return = statistics.mean(returns)
            
            # Recent trend analysis (last 5 periods)
            recent_returns = returns[-5:] if len(returns) >= 5 else returns
            recent_trend = statistics.mean(recent_returns)
            
            # Momentum analysis
            short_ma = statistics.mean(prices[-5:]) if len(prices) >= 5 else current_price
            long_ma = statistics.mean(prices[-10:]) if len(prices) >= 10 else current_price
            momentum = (short_ma - long_ma) / long_ma * 100
            
            # Calculate crash probability based on multiple factors
            crash_probability = 0
            
            # Factor 1: High volatility (0-30 points)
            volatility_score = min(volatility / 2.0, 30)  # Cap at 30
            crash_probability += volatility_score
            
            # Factor 2: Negative trend (0-25 points)
            if recent_trend < 0:
                trend_score = min(abs(recent_trend) * 2, 25)
                crash_probability += trend_score
            
            # Factor 3: Negative momentum (0-20 points)
            if momentum < 0:
                momentum_score = min(abs(momentum), 20)
                crash_probability += momentum_score
            
            # Factor 4: Consecutive negative returns (0-15 points)
            negative_streak = 0
            for ret in reversed(recent_returns):
                if ret < 0:
                    negative_streak += 1
                else:
                    break
            
            streak_score = min(negative_streak * 3, 15)
            crash_probability += streak_score
            
            # Factor 5: Large recent drop (0-10 points)
            if len(returns) > 0 and returns[-1] < -2:  # Last return < -2%
                drop_score = min(abs(returns[-1]), 10)
                crash_probability += drop_score
            
            # Cap at 100%
            crash_probability = min(crash_probability, 100)
            
            # Simple prediction: assume trend continues
            predicted_change = recent_trend
            predicted_price = current_price * (1 + predicted_change / 100)
            predicted_drop = ((predicted_price - current_price) / current_price) * 100
            
            return {
                'crash_detected': crash_probability > 60,
                'crash_probability': round(crash_probability, 1),
                'predicted_drop': round(predicted_drop, 2),
                'crash_horizon_minutes': 5,  # Simple assumption
                'predicted_prices': [predicted_price],
                'lower_bound': [predicted_price * 0.95],
                'upper_bound': [predicted_price * 1.05],
                'uncertainty': round(volatility, 2),
                'trend_strength': round(abs(recent_trend) / 10, 2),
                'volatility': round(volatility, 2),
                'momentum': round(momentum, 2),
                'negative_streak': negative_streak,
                'method': 'Simple Statistical Analysis',
                'symbol': symbol,
                'current_price': current_price,
                'timestamp': datetime.now().isoformat(),
                'factors': {
                    'volatility_score': round(volatility_score, 1),
                    'trend_score': round(trend_score if recent_trend < 0 else 0, 1),
                    'momentum_score': round(momentum_score if momentum < 0 else 0, 1),
                    'streak_score': round(streak_score, 1),
                    'drop_score': round(drop_score if len(returns) > 0 and returns[-1] < -2 else 0, 1)
                }
            }
            
        except Exception as e:
            return {
                'crash_detected': False,
                'crash_probability': 0,
                'error': f'Simple crash detection failed: {str(e)}'
            }
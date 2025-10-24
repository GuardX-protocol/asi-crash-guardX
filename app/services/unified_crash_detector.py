"""
Unified Crash Detection Service
Combines Prophet, ARIMA, and Anomaly Detection
NO TRAINING REQUIRED - All methods auto-fit
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

from .prophet_crash_detector import ProphetCrashDetector
from .arima_crash_detector import ARIMACrashDetector
from .anomaly_crash_detector import AnomalyBasedCrashDetector

class UnifiedCrashDetector:
    """
    Combines multiple training-free prediction methods:
    - Facebook Prophet (time series forecasting)
    - Auto-ARIMA (statistical modeling)
    - Isolation Forest (anomaly detection)
    """
    
    def __init__(self):
        self.prophet = ProphetCrashDetector()
        self.arima = ARIMACrashDetector()
        self.anomaly = AnomalyBasedCrashDetector()
        
        # Price data cache
        self.price_cache = {}
        self.max_cache_size = 200  # Keep last 200 data points
    
    async def get_price_data(self, symbol: str, interval: str = '1m', limit: int = 100) -> Dict:
        """Get recent price data from Binance"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return {'error': f'Binance API error: {response.status_code}'}
            
            data = response.json()
            
            # Extract prices and timestamps
            timestamps = []
            prices = []
            volumes = []
            
            for kline in data:
                timestamp = datetime.fromtimestamp(kline[0] / 1000)
                close_price = float(kline[4])
                volume = float(kline[5])
                
                timestamps.append(timestamp)
                prices.append(close_price)
                volumes.append(volume)
            
            # Cache the data
            self.price_cache[symbol] = {
                'timestamps': timestamps,
                'prices': prices,
                'volumes': volumes,
                'last_update': datetime.now()
            }
            
            return {
                'timestamps': timestamps,
                'prices': prices,
                'volumes': volumes,
                'symbol': symbol
            }
            
        except Exception as e:
            return {'error': f'Failed to get price data: {str(e)}'}
    
    async def comprehensive_crash_analysis(self, symbol: str) -> Dict:
        """
        Run comprehensive crash analysis using all methods
        Returns unified results with confidence scoring
        """
        try:
            # Get fresh price data
            price_data = await self.get_price_data(symbol)
            
            if 'error' in price_data:
                return {
                    'symbol': symbol,
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': price_data['error'],
                    'timestamp': datetime.now().isoformat()
                }
            
            timestamps = price_data['timestamps']
            prices = price_data['prices']
            current_price = prices[-1]
            
            # Run all detection methods
            results = {}
            
            # 1. Prophet Analysis
            try:
                prophet_result = self.prophet.predict_crash(
                    symbol, prices, timestamps, periods=10
                )
                results['prophet'] = prophet_result
            except Exception as e:
                results['prophet'] = {'error': str(e), 'crash_probability': 0}
            
            # 2. ARIMA Analysis
            try:
                arima_result = self.arima.predict_crash(symbol, prices, periods=10)
                results['arima'] = arima_result
            except Exception as e:
                results['arima'] = {'error': str(e), 'crash_probability': 0}
            
            # 3. Anomaly Detection
            try:
                anomaly_result = self.anomaly.detect_crash(symbol, prices)
                results['anomaly'] = anomaly_result
            except Exception as e:
                results['anomaly'] = {'error': str(e), 'crash_probability': 0}
            
            # Combine results
            unified_result = self.combine_predictions(results, symbol, current_price)
            
            # Add market context
            unified_result.update(self.add_market_context(prices, price_data['volumes']))
            
            return unified_result
            
        except Exception as e:
            return {
                'symbol': symbol,
                'crash_detected': False,
                'crash_probability': 0,
                'error': f'Comprehensive analysis failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def combine_predictions(self, results: Dict, symbol: str, current_price: float) -> Dict:
        """Combine predictions from all methods with weighted scoring"""
        
        # Extract probabilities
        prophet_prob = results.get('prophet', {}).get('crash_probability', 0)
        arima_prob = results.get('arima', {}).get('crash_probability', 0)
        anomaly_prob = results.get('anomaly', {}).get('crash_probability', 0)
        
        # Method weights (based on crypto prediction research)
        weights = {
            'prophet': 0.4,    # Strong for trend prediction
            'arima': 0.35,     # Good for short-term forecasting
            'anomaly': 0.25    # Good for detecting unusual patterns
        }
        
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        if prophet_prob > 0:
            weighted_sum += prophet_prob * weights['prophet']
            total_weight += weights['prophet']
        
        if arima_prob > 0:
            weighted_sum += arima_prob * weights['arima']
            total_weight += weights['arima']
        
        if anomaly_prob > 0:
            weighted_sum += anomaly_prob * weights['anomaly']
            total_weight += weights['anomaly']
        
        # Final crash probability
        if total_weight > 0:
            crash_probability = weighted_sum / total_weight
        else:
            crash_probability = 0
        
        # Consensus scoring (bonus if multiple methods agree)
        methods_detecting = sum([
            1 for prob in [prophet_prob, arima_prob, anomaly_prob] 
            if prob > 60
        ])
        
        if methods_detecting >= 2:
            crash_probability += 10  # Consensus bonus
        
        # Determine warning level
        if crash_probability >= 80:
            warning_level = "CRITICAL"
            severity = "HIGH"
        elif crash_probability >= 65:
            warning_level = "HIGH"
            severity = "MEDIUM"
        elif crash_probability >= 50:
            warning_level = "MODERATE"
            severity = "MEDIUM"
        else:
            warning_level = "LOW"
            severity = "LOW"
        
        return {
            'symbol': symbol,
            'crash_detected': crash_probability >= 60,
            'crash_probability': min(crash_probability, 100),
            'warning_level': warning_level,
            'severity': severity,
            'current_price': current_price,
            'methods_consensus': methods_detecting,
            'individual_results': {
                'prophet': prophet_prob,
                'arima': arima_prob,
                'anomaly': anomaly_prob
            },
            'detailed_results': results,
            'timestamp': datetime.now().isoformat(),
            'analysis_method': 'Unified Training-Free Detection'
        }
    
    def add_market_context(self, prices: List[float], volumes: List[float]) -> Dict:
        """Add market context indicators"""
        
        # Price volatility
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        volatility = np.std(returns) * 100
        
        # Volume analysis
        avg_volume = np.mean(volumes[-10:])  # Last 10 periods
        recent_volume = volumes[-1]
        volume_spike = recent_volume > (avg_volume * 1.5)
        
        # Price momentum
        short_ma = np.mean(prices[-5:])   # 5-period MA
        long_ma = np.mean(prices[-20:])   # 20-period MA
        momentum = ((short_ma - long_ma) / long_ma) * 100
        
        # Support/resistance levels
        recent_high = max(prices[-20:])
        recent_low = min(prices[-20:])
        current_price = prices[-1]
        
        # Market sentiment
        if momentum > 2:
            sentiment = "BULLISH"
        elif momentum < -2:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
        
        return {
            'volatility': volatility,
            'volume_spike': volume_spike,
            'volume_ratio': recent_volume / avg_volume if avg_volume > 0 else 1,
            'momentum': momentum,
            'market_sentiment': sentiment,
            'support_level': recent_low,
            'resistance_level': recent_high,
            'price_position': ((current_price - recent_low) / (recent_high - recent_low)) * 100 if recent_high > recent_low else 50,
            'evidence': {
                'volatility': {'value': volatility, 'signal': 'high' if volatility > 3 else 'normal'},
                'volume': {'spike': volume_spike, 'ratio': recent_volume / avg_volume if avg_volume > 0 else 1},
                'momentum': {'value': momentum, 'signal': 'bearish' if momentum < -2 else 'bullish' if momentum > 2 else 'neutral'},
                'support_break': current_price < (recent_low * 1.02),  # Within 2% of support
                'resistance_test': current_price > (recent_high * 0.98)  # Within 2% of resistance
            }
        }
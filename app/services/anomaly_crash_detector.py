"""
Isolation Forest Anomaly Detection - Zero Training
Detects anomalies without training on labeled data
"""

from sklearn.ensemble import IsolationForest
import numpy as np
from datetime import datetime

class AnomalyBasedCrashDetector:
    """
    Isolation Forest - Unsupervised, NO TRAINING on labels
    Automatically detects anomalies in price patterns
    """
    
    def __init__(self):
        self.models = {}
    
    def detect_crash(self, symbol, price_history, window_size=20):
        """
        Detect crashes using anomaly detection
        """
        try:
            if len(price_history) < window_size:
                return {
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': f'Insufficient data (need {window_size}+ points)'
                }
            
            # Create features from price history
            features = self.create_features(price_history, window_size)
            
            if len(features) == 0:
                return {
                    'crash_detected': False,
                    'crash_probability': 0,
                    'error': 'Could not create features'
                }
            
            # Fit Isolation Forest (unsupervised - no labels needed!)
            model = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100
            )
            
            # Fit and predict in one go
            anomaly_scores = model.fit_predict(features)
            decision_scores = model.decision_function(features)
            
            # Check recent points for anomalies
            recent_window = min(5, len(anomaly_scores))
            recent_anomalies = anomaly_scores[-recent_window:]
            recent_scores = decision_scores[-recent_window:]
            
            # Calculate crash probability
            anomaly_count = sum(recent_anomalies == -1)
            avg_score = np.mean(recent_scores)
            
            # Anomaly-based crash probability
            anomaly_ratio = anomaly_count / recent_window
            score_factor = max(0, 1 - abs(avg_score))  # Lower scores = more anomalous
            
            crash_probability = (anomaly_ratio * 60) + (score_factor * 40)
            
            # Additional volatility check
            recent_prices = price_history[-recent_window:]
            volatility = np.std(recent_prices) / np.mean(recent_prices) * 100
            
            if volatility > 5:  # High volatility
                crash_probability += 15
            
            return {
                'crash_detected': crash_probability > 70,
                'crash_probability': min(crash_probability, 100),
                'anomaly_count': anomaly_count,
                'anomaly_ratio': anomaly_ratio,
                'anomaly_scores': recent_scores.tolist(),
                'volatility': volatility,
                'method': 'Isolation Forest',
                'symbol': symbol,
                'current_price': price_history[-1],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'crash_detected': False,
                'crash_probability': 0,
                'error': f'Anomaly detection failed: {str(e)}'
            }
    
    def create_features(self, prices, window):
        """Extract features for anomaly detection"""
        features = []
        
        for i in range(window, len(prices)):
            window_prices = prices[i-window:i]
            current_price = prices[i]
            
            # Price statistics
            mean_price = np.mean(window_prices)
            std_price = np.std(window_prices)
            min_price = np.min(window_prices)
            max_price = np.max(window_prices)
            
            # Returns and volatility
            returns = [(prices[j] - prices[j-1]) / prices[j-1] for j in range(i-window+1, i)]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Price position in window
            price_percentile = np.percentile(window_prices, 
                                           [(current_price - min_price) / (max_price - min_price) * 100])[0]
            
            # Trend indicators
            trend = (window_prices[-1] - window_prices[0]) / window_prices[0]
            
            features.append([
                mean_price,
                std_price,
                max_price - min_price,  # Range
                (current_price - mean_price) / std_price if std_price > 0 else 0,  # Z-score
                mean_return,
                std_return,
                price_percentile,
                trend,
                np.percentile(window_prices, 25),
                np.percentile(window_prices, 75)
            ])
        
        return np.array(features)
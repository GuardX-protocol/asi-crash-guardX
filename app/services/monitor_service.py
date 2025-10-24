"""
Monitor Service - Actively monitors user-created monitors and sends alerts
"""

import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from app.database import is_connected
from app.models import Monitor, MonitorAlert, User
from app.services.fallback_storage import fallback_storage
from app.services.prophet_crash_detector import ProphetCrashDetector

logger = logging.getLogger(__name__)

class MonitorService:
    def __init__(self):
        self.running = False
        self.crash_detector = ProphetCrashDetector()
        self.price_history = {}  # Store price history for each symbol
        self.last_prices = {}    # Store last known prices
        self.monitor_intervals = {}  # Track individual monitor intervals
        
    async def start_monitoring(self):
        """Start the monitoring service"""
        if self.running:
            logger.warning("Monitor service is already running")
            return
            
        self.running = True
        logger.info("🔍 Starting Monitor Service...")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        logger.info("✅ Monitor Service started")
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        self.running = False
        logger.info("🛑 Monitor Service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                # Get all active monitors
                active_monitors = await self._get_active_monitors()
                
                if not active_monitors:
                    logger.debug("No active monitors found")
                    await asyncio.sleep(30)  # Check every 30 seconds if no monitors
                    continue
                
                logger.info(f"📊 Monitoring {len(active_monitors)} active monitors")
                
                # Process each monitor
                for monitor in active_monitors:
                    try:
                        await self._process_monitor(monitor)
                    except Exception as e:
                        logger.error(f"Error processing monitor {monitor.name}: {e}")
                
                consecutive_errors = 0  # Reset error counter on success
                
                # Wait before next cycle (minimum 60 seconds)
                await asyncio.sleep(60)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Monitor loop error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, stopping monitor service")
                    break
                
                # Exponential backoff on errors
                await asyncio.sleep(min(30 * (2 ** consecutive_errors), 300))
        
        self.running = False
        logger.info("🔍 Monitor Service loop ended")
    
    async def _get_active_monitors(self) -> List[Monitor]:
        """Get all active monitors from database"""
        try:
            if is_connected():
                monitors = await Monitor.find(Monitor.enabled == True).to_list()
            else:
                all_monitors = await fallback_storage.get_monitors()
                monitors = [m for m in all_monitors if getattr(m, 'enabled', False)]
            
            return monitors
        except Exception as e:
            logger.error(f"Error getting active monitors: {e}")
            return []
    
    async def _process_monitor(self, monitor: Monitor):
        """Process a single monitor"""
        try:
            # Check if it's time to process this monitor
            if not await self._should_process_monitor(monitor):
                return
            
            logger.debug(f"Processing monitor: {monitor.name}")
            
            # Get current prices for all symbols in this monitor
            symbol_prices = await self._get_symbol_prices(monitor.symbols)
            
            if not symbol_prices:
                logger.warning(f"No prices available for monitor {monitor.name}")
                return
            
            # Process each symbol
            for symbol in monitor.symbols:
                if symbol not in symbol_prices:
                    continue
                
                current_price = symbol_prices[symbol]
                await self._analyze_symbol(monitor, symbol, current_price)
            
            # Update last processed time
            self.monitor_intervals[monitor.name] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error processing monitor {monitor.name}: {e}")
    
    async def _should_process_monitor(self, monitor: Monitor) -> bool:
        """Check if monitor should be processed based on its interval"""
        if monitor.name not in self.monitor_intervals:
            return True  # First time processing
        
        last_processed = self.monitor_intervals[monitor.name]
        interval_seconds = getattr(monitor, 'interval_seconds', 300)  # Default 5 minutes
        
        time_since_last = (datetime.utcnow() - last_processed).total_seconds()
        return time_since_last >= interval_seconds
    
    async def _get_symbol_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        try:
            prices = {}
            
            for symbol in symbols:
                # Ensure symbol has USDT suffix for Binance
                binance_symbol = symbol if symbol.endswith('USDT') else f"{symbol}USDT"
                
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            prices[symbol] = float(data['price'])
                        else:
                            logger.warning(f"Failed to get price for {symbol}: {response.status}")
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting symbol prices: {e}")
            return {}
    
    async def _analyze_symbol(self, monitor: Monitor, symbol: str, current_price: float):
        """Analyze a symbol for crash conditions"""
        try:
            # Update price history
            await self._update_price_history(symbol, current_price)
            
            # Get price history for analysis
            price_history = self.price_history.get(symbol, [])
            
            if len(price_history) < 10:
                logger.debug(f"Insufficient price history for {symbol} ({len(price_history)} points)")
                return
            
            # Check basic thresholds first
            alerts = []
            
            # Price change analysis
            if len(price_history) >= 2:
                price_change = ((current_price - price_history[-2]) / price_history[-2]) * 100
                
                if abs(price_change) >= monitor.price_change_threshold:
                    alerts.append({
                        'type': 'price_change',
                        'severity': 'high' if abs(price_change) >= monitor.price_change_threshold * 2 else 'medium',
                        'value': price_change,
                        'threshold': monitor.price_change_threshold
                    })
            
            # Crash probability analysis using Prophet
            if len(price_history) >= 30:  # Minimum for Prophet
                timestamps = [datetime.utcnow() - timedelta(minutes=i) for i in range(len(price_history)-1, -1, -1)]
                
                crash_analysis = self.crash_detector.predict_crash(
                    symbol, price_history, timestamps, periods=10
                )
                
                if crash_analysis.get('crash_probability', 0) >= monitor.crash_probability_threshold:
                    alerts.append({
                        'type': 'crash_detection',
                        'severity': 'high' if crash_analysis['crash_probability'] >= 80 else 'medium',
                        'value': crash_analysis['crash_probability'],
                        'threshold': monitor.crash_probability_threshold,
                        'analysis': crash_analysis
                    })
            
            # Send alerts if any conditions are met
            for alert_data in alerts:
                await self._send_alert(monitor, symbol, current_price, alert_data)
                
        except Exception as e:
            logger.error(f"Error analyzing symbol {symbol}: {e}")
    
    async def _update_price_history(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        
        # Keep only last 100 price points to manage memory
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        self.last_prices[symbol] = price
    
    async def _send_alert(self, monitor: Monitor, symbol: str, current_price: float, alert_data: Dict[str, Any]):
        """Send alert to user"""
        try:
            # Create alert record
            alert_record = {
                'monitorId': str(monitor.id) if hasattr(monitor, 'id') else monitor.name,
                'userId': monitor.userId,
                'symbol': symbol,
                'alertType': alert_data['type'],
                'crash_probability': alert_data.get('analysis', {}).get('crash_probability'),
                'price_change': alert_data.get('value') if alert_data['type'] == 'price_change' else None,
                'current_price': current_price,
                'asi_analysis': self._generate_analysis_text(alert_data),
                'technical_indicators': alert_data.get('analysis', {}),
                'severity': alert_data['severity'],
                'sent_telegram': False,
                'sent_email': False,
                'sent_webhook': False,
                'createdAt': datetime.utcnow()
            }
            
            # Save alert to database
            if is_connected():
                new_alert = MonitorAlert(**alert_record)
                await new_alert.insert()
                alert_id = str(new_alert.id)
            else:
                alert_id = await fallback_storage.create_alert(alert_record)
            
            # Send Telegram alert if enabled
            if getattr(monitor, 'telegram_alerts', False):
                await self._send_telegram_alert(monitor, symbol, current_price, alert_data, alert_id)
            
            # Send webhook alerts if configured
            if getattr(monitor, 'alert_webhooks', []):
                await self._send_webhook_alerts(monitor, symbol, current_price, alert_data, alert_id)
            
            logger.info(f"🚨 Alert sent for {symbol} on monitor {monitor.name}: {alert_data['type']}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _send_telegram_alert(self, monitor: Monitor, symbol: str, current_price: float, alert_data: Dict[str, Any], alert_id: str):
        """Send Telegram alert"""
        try:
            # Call the telegram alert endpoint
            alert_payload = {
                'user_id': monitor.userId,
                'symbol': symbol,
                'alert_type': alert_data['type'],
                'crash_probability': alert_data.get('analysis', {}).get('crash_probability'),
                'price_change': alert_data.get('value') if alert_data['type'] == 'price_change' else None,
                'current_price': current_price,
                'severity': alert_data['severity'],
                'additional_info': self._generate_analysis_text(alert_data)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://localhost:8000/telegram/send-alert',
                    json=alert_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        # Update alert record
                        await self._update_alert_status(alert_id, 'sent_telegram', True)
                        logger.info(f"✅ Telegram alert sent for {symbol}")
                    else:
                        error_text = await response.text()
                        logger.warning(f"Failed to send Telegram alert: {response.status} - {error_text}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    async def _send_webhook_alerts(self, monitor: Monitor, symbol: str, current_price: float, alert_data: Dict[str, Any], alert_id: str):
        """Send webhook alerts"""
        webhooks = getattr(monitor, 'alert_webhooks', [])
        
        for webhook_url in webhooks:
            try:
                webhook_payload = {
                    'monitor_name': monitor.name,
                    'user_id': monitor.userId,
                    'symbol': symbol,
                    'alert_type': alert_data['type'],
                    'severity': alert_data['severity'],
                    'current_price': current_price,
                    'threshold': alert_data['threshold'],
                    'value': alert_data['value'],
                    'analysis': alert_data.get('analysis', {}),
                    'timestamp': datetime.utcnow().isoformat(),
                    'alert_id': alert_id
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=webhook_payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            logger.info(f"✅ Webhook alert sent to {webhook_url}")
                        else:
                            logger.warning(f"Webhook failed {webhook_url}: {response.status}")
                
            except Exception as e:
                logger.error(f"Error sending webhook to {webhook_url}: {e}")
    
    async def _update_alert_status(self, alert_id: str, field: str, value: bool):
        """Update alert delivery status"""
        try:
            if is_connected():
                from bson import ObjectId
                alert = await MonitorAlert.find_one(MonitorAlert.id == ObjectId(alert_id))
                if alert:
                    await alert.update({"$set": {field: value}})
            else:
                await fallback_storage.update_alert(alert_id, {field: value})
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
    
    def _generate_analysis_text(self, alert_data: Dict[str, Any]) -> str:
        """Generate human-readable analysis text"""
        alert_type = alert_data['type']
        severity = alert_data['severity']
        
        if alert_type == 'price_change':
            change = alert_data['value']
            direction = "dropped" if change < 0 else "increased"
            return f"Price {direction} by {abs(change):.2f}% in the last interval. This exceeds the {alert_data['threshold']}% threshold set for this monitor."
        
        elif alert_type == 'crash_detection':
            analysis = alert_data.get('analysis', {})
            prob = analysis.get('crash_probability', 0)
            drop = analysis.get('predicted_drop', 0)
            horizon = analysis.get('crash_horizon_minutes', 0)
            
            return f"Crash detection algorithm predicts {prob:.1f}% probability of significant price decline. Potential drop of {abs(drop):.2f}% expected within {horizon} minutes. High volatility and downward trend detected."
        
        return f"Alert triggered for {alert_type} with {severity} severity."
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring service status"""
        return {
            'running': self.running,
            'symbols_tracked': len(self.price_history),
            'monitors_tracked': len(self.monitor_intervals),
            'last_prices': dict(list(self.last_prices.items())[:10]),  # Show first 10
            'price_history_lengths': {k: len(v) for k, v in list(self.price_history.items())[:10]}
        }

# Global instance
monitor_service = MonitorService()

async def start_monitor_service():
    """Start the monitor service"""
    await monitor_service.start_monitoring()

def stop_monitor_service():
    """Stop the monitor service"""
    monitor_service.stop_monitoring()

def get_monitor_service_status():
    """Get monitor service status"""
    return monitor_service.get_status()
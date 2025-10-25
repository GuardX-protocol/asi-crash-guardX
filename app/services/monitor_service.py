"""
Enhanced monitor service with ASI crash detection and multi-channel notifications
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
import os

from app.database import ensure_connection
from app.models import Monitor, MonitorAlert, User
from app.services.binance_api import binance_api
from app.services.asi_crash_detector import asi_crash_detector
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

class EnhancedMonitorService:
    def __init__(self):
        self.is_running = False
        self.monitored_symbols: Set[str] = set()
        self.check_interval = 300  # Check every 5 minutes for better API rate limiting
        self.price_history: Dict[str, List[Dict]] = {}
        self.last_alerts: Dict[str, datetime] = {}  # Prevent spam alerts
        self.alert_cooldown = 3600  # 1 hour cooldown between alerts for same symbol
        
    async def start_monitoring(self):
        """Start the enhanced monitoring service"""
        if self.is_running:
            logger.warning("Monitor service is already running")
            return
            
        self.is_running = True
        logger.info("🔍 Starting enhanced monitor service with ASI integration...")
        
        # Load active monitors
        await self._load_active_monitors()
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
    def stop_monitoring(self):
        """Stop the monitoring service"""
        self.is_running = False
        logger.info("🔍 Enhanced monitor service stopped")
        
    async def _load_active_monitors(self):
        """Load all active monitors and their symbols with detailed logging"""
        try:
            if not await ensure_connection():
                logger.error("❌ Database connection failed - cannot load monitors")
                return
                
            monitors = await Monitor.find(Monitor.enabled == True).to_list()
            
            logger.info(f"📊 LOADING ACTIVE MONITORS:")
            logger.info(f"   🔍 Found {len(monitors)} active monitors in database")
            
            self.monitored_symbols.clear()
            monitor_details = []
            
            for monitor in monitors:
                user_wallet = monitor.userId
                monitor_symbols = len(monitor.symbols)
                threshold = monitor.crash_threshold
                channels = ', '.join(monitor.notification_channels)
                
                monitor_details.append({
                    'name': monitor.name,
                    'user': user_wallet[:10] + '...' if len(user_wallet) > 10 else user_wallet,
                    'symbols': monitor_symbols,
                    'threshold': threshold,
                    'channels': channels
                })
                
                for symbol in monitor.symbols:
                    self.monitored_symbols.add(symbol)
                    
                logger.info(f"   📋 Monitor: {monitor.name}")
                logger.info(f"      👤 User: {user_wallet[:10]}...")
                logger.info(f"      🪙 Symbols: {', '.join(monitor.symbols)}")
                logger.info(f"      📉 Threshold: {threshold}%")
                logger.info(f"      📢 Channels: {channels}")
                logger.info(f"      ✅ Status: {'Enabled' if monitor.enabled else 'Disabled'}")
                    
            unique_symbols = list(self.monitored_symbols)
            logger.info(f"📊 MONITORING SUMMARY:")
            logger.info(f"   🔍 Total Monitors: {len(monitors)}")
            logger.info(f"   🪙 Unique Symbols: {len(unique_symbols)}")
            logger.info(f"   📋 Symbol List: {', '.join(sorted(unique_symbols))}")
            logger.info(f"   ⏱️ Check Interval: {self.check_interval} seconds ({self.check_interval//60} minutes)")
            logger.info(f"   🔄 Alert Cooldown: {self.alert_cooldown} seconds ({self.alert_cooldown//3600} hour)")
            logger.info(f"   🤖 ASI Integration: {'✅ Enabled' if asi_crash_detector.is_configured() else '❌ Disabled'}")
            logger.info(f"   📧 Email Service: {'✅ Enabled' if email_service.is_configured() else '❌ Disabled'}")
            
        except Exception as e:
            logger.error(f"❌ Error loading active monitors: {e}")
            logger.error(f"   🔍 Error Type: {type(e).__name__}")
            logger.error(f"   📝 Error Details: {str(e)[:200]}...")
            
    async def _monitoring_loop(self):
        """Main monitoring loop with comprehensive logging"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        loop_count = 0
        
        logger.info(f"🔄 STARTING MONITORING LOOP:")
        logger.info(f"   ⏱️ Check Interval: {self.check_interval} seconds")
        logger.info(f"   🔄 Max Errors: {max_consecutive_errors}")
        logger.info(f"   🪙 Symbols to Monitor: {len(self.monitored_symbols)}")
        
        while self.is_running:
            try:
                loop_count += 1
                start_time = datetime.utcnow()
                
                logger.info(f"🔍 MONITORING CYCLE #{loop_count} - {start_time.strftime('%H:%M:%S')} UTC")
                logger.info(f"   📊 Checking {len(self.monitored_symbols)} symbols for crashes...")
                
                # Check all symbols
                crashes_detected = await self._check_all_symbols()
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.info(f"✅ MONITORING CYCLE #{loop_count} COMPLETE:")
                logger.info(f"   ⏱️ Duration: {duration:.2f} seconds")
                logger.info(f"   🚨 Crashes Detected: {crashes_detected}")
                logger.info(f"   📊 Symbols Checked: {len(self.monitored_symbols)}")
                logger.info(f"   🔄 Next Check: {(datetime.utcnow() + timedelta(seconds=self.check_interval)).strftime('%H:%M:%S')} UTC")
                
                consecutive_errors = 0  # Reset error counter on success
                
                # Log next check time
                logger.info(f"⏳ Waiting {self.check_interval} seconds until next monitoring cycle...")
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ MONITORING LOOP ERROR (attempt {consecutive_errors}/{max_consecutive_errors}):")
                logger.error(f"   🔍 Error Type: {type(e).__name__}")
                logger.error(f"   📝 Error Message: {str(e)}")
                logger.error(f"   🔄 Loop Count: {loop_count}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"🚨 CRITICAL: Too many consecutive errors ({consecutive_errors})")
                    logger.critical(f"   🛑 Stopping monitor service for safety")
                    self.is_running = False
                    break
                    
                # Exponential backoff on errors
                sleep_time = min(self.check_interval * (2 ** consecutive_errors), 1800)  # Max 30 min
                logger.warning(f"   ⏳ Backing off for {sleep_time} seconds before retry...")
                await asyncio.sleep(sleep_time)
        
        logger.info(f"🔄 MONITORING LOOP ENDED after {loop_count} cycles")
                
    async def _check_all_symbols(self):
        """Check all monitored symbols for crashes with detailed logging"""
        if not self.monitored_symbols:
            logger.warning("⚠️ No symbols to monitor - reloading monitors...")
            await self._load_active_monitors()  # Reload if empty
            return 0
        
        crashes_detected = 0
        symbols_checked = 0
        api_errors = 0
        
        # Process symbols in batches to avoid rate limiting
        symbol_list = list(self.monitored_symbols)
        batch_size = 5
        
        logger.info(f"   📊 Processing {len(symbol_list)} symbols in batches of {batch_size}")
        
        for i in range(0, len(symbol_list), batch_size):
            batch = symbol_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(symbol_list) + batch_size - 1) // batch_size
            
            logger.info(f"   🔄 Processing Batch {batch_num}/{total_batches}: {', '.join(batch)}")
            
            # Process batch concurrently
            batch_start = datetime.utcnow()
            tasks = [self._check_symbol(symbol) for symbol in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_duration = (datetime.utcnow() - batch_start).total_seconds()
            
            # Process results
            batch_crashes = 0
            batch_errors = 0
            
            for j, result in enumerate(results):
                symbols_checked += 1
                if isinstance(result, Exception):
                    batch_errors += 1
                    api_errors += 1
                    logger.error(f"      ❌ {batch[j]}: {str(result)[:100]}")
                elif result:
                    batch_crashes += 1
                    crashes_detected += 1
                    logger.warning(f"      🚨 {batch[j]}: CRASH DETECTED!")
                else:
                    logger.debug(f"      ✅ {batch[j]}: Normal conditions")
            
            logger.info(f"   ✅ Batch {batch_num} Complete:")
            logger.info(f"      ⏱️ Duration: {batch_duration:.2f}s")
            logger.info(f"      🚨 Crashes: {batch_crashes}")
            logger.info(f"      ❌ Errors: {batch_errors}")
            
            # Small delay between batches
            if i + batch_size < len(symbol_list):
                logger.debug(f"   ⏳ Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        # Final summary
        success_rate = ((symbols_checked - api_errors) / symbols_checked * 100) if symbols_checked > 0 else 0
        logger.info(f"📊 SYMBOL CHECK SUMMARY:")
        logger.info(f"   ✅ Symbols Checked: {symbols_checked}")
        logger.info(f"   🚨 Crashes Detected: {crashes_detected}")
        logger.info(f"   ❌ API Errors: {api_errors}")
        logger.info(f"   📈 Success Rate: {success_rate:.1f}%")
        
        return crashes_detected
                
    async def _check_symbol(self, symbol: str):
        """Enhanced symbol checking with comprehensive ASI logging"""
        try:
            symbol_start_time = datetime.utcnow()
            
            # Check cooldown
            if symbol in self.last_alerts:
                time_since_last = datetime.utcnow() - self.last_alerts[symbol]
                if time_since_last.total_seconds() < self.alert_cooldown:
                    cooldown_remaining = self.alert_cooldown - time_since_last.total_seconds()
                    logger.debug(f"      ⏳ {symbol}: Alert cooldown active ({cooldown_remaining/60:.1f}m remaining)")
                    return False
            
            # Get current price
            logger.debug(f"      💰 {symbol}: Fetching current price...")
            price_data = await binance_api.get_symbol_price(symbol)
            if not price_data:
                logger.warning(f"      ❌ {symbol}: No price data available")
                raise Exception(f"No price data for {symbol}")
                
            current_price = float(price_data["price"])
            logger.debug(f"      💸 {symbol}: Current price ${current_price:,.4f}")
            
            # Get historical data for analysis
            logger.debug(f"      📊 {symbol}: Fetching historical data (168 hours)...")
            klines = await binance_api.get_klines(symbol, "1h", 168)  # 7 days of hourly data
            if not klines or len(klines) < 24:
                logger.warning(f"      ❌ {symbol}: Insufficient historical data ({len(klines) if klines else 0} points)")
                raise Exception(f"Insufficient data for {symbol}")
                
            logger.debug(f"      📈 {symbol}: Historical data loaded ({len(klines)} data points)")
            
            # Update price history
            self.price_history[symbol] = klines
            
            # Run enhanced crash detection with ASI
            logger.debug(f"      🤖 {symbol}: Running crash detection analysis...")
            detection_start = datetime.utcnow()
            
            crash_result = await asi_crash_detector.detect_crash(symbol, klines, current_price)
            
            detection_duration = (datetime.utcnow() - detection_start).total_seconds()
            
            if crash_result:
                crash_prob = crash_result.get('crash_probability', 0)
                is_crash = crash_result.get("is_crash", False)
                confidence = crash_result.get('confidence_level', 'unknown')
                asi_analysis = crash_result.get('asi_analysis')
                
                logger.info(f"      🔍 {symbol}: CRASH ANALYSIS COMPLETE")
                logger.info(f"         💰 Price: ${current_price:,.4f}")
                logger.info(f"         🎯 Crash Probability: {crash_prob:.1f}%")
                logger.info(f"         🔍 Confidence: {confidence}")
                logger.info(f"         🚨 Crash Detected: {'YES' if is_crash else 'NO'}")
                logger.info(f"         ⏱️ Analysis Duration: {detection_duration:.2f}s")
                
                # Log ASI analysis status
                if asi_analysis:
                    logger.info(f"         🤖 ASI Analysis: ✅ RECEIVED")
                    logger.info(f"            📝 Length: {len(asi_analysis.get('raw_analysis', ''))} chars")
                    logger.info(f"            🎯 ASI Confidence: {asi_analysis.get('confidence', 'unknown')}")
                    logger.info(f"            🤖 Model: {asi_analysis.get('model', 'unknown')}")
                    
                    # Log preview of ASI analysis
                    analysis_preview = asi_analysis.get('raw_analysis', '')[:150]
                    if analysis_preview:
                        logger.info(f"            📊 Preview: {analysis_preview}...")
                else:
                    logger.info(f"         🤖 ASI Analysis: ❌ NOT AVAILABLE")
                    if crash_prob > 0.3:
                        logger.warning(f"            ⚠️ Expected ASI analysis (probability > 30%)")
                
                # Log technical indicators
                technical = crash_result.get('technical_signals', {})
                active_signals = [k for k, v in technical.items() if v and k != 'error']
                logger.info(f"         📊 Technical Signals: {len(active_signals)} active")
                if active_signals:
                    logger.debug(f"            🔍 Signals: {', '.join(active_signals[:5])}")
                
                if is_crash:
                    logger.warning(f"      🚨 {symbol}: CRASH DETECTED - Processing alerts...")
                    await self._handle_crash_detected(symbol, crash_result)
                    return True
                else:
                    logger.debug(f"      ✅ {symbol}: Normal market conditions")
                    return False
            else:
                logger.error(f"      ❌ {symbol}: Crash detection failed - no results")
                raise Exception(f"Crash detection failed for {symbol}")
                
        except Exception as e:
            symbol_duration = (datetime.utcnow() - symbol_start_time).total_seconds()
            logger.error(f"      ❌ {symbol}: Error after {symbol_duration:.2f}s - {str(e)[:100]}")
            raise e
            
    async def _handle_crash_detected(self, symbol: str, crash_result: Dict):
        """Enhanced crash handling with comprehensive logging"""
        try:
            crash_prob = crash_result.get('crash_probability', 0)
            price_drop = abs(crash_result.get("price_drop_24h", 0))
            current_price = crash_result.get('current_price', 0)
            token_name = self._get_token_name(symbol)
            
            logger.warning(f"🚨 CRASH HANDLING: {token_name} ({symbol})")
            logger.warning(f"   💰 Current Price: ${current_price:,.4f}")
            logger.warning(f"   📉 Price Drop: {price_drop:.2f}%")
            logger.warning(f"   🎯 Crash Probability: {crash_prob:.1f}%")
            logger.warning(f"   ⏰ Detection Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC")
            
            # Find all monitors watching this symbol
            monitors = await Monitor.find(
                Monitor.symbols.in_([symbol]),
                Monitor.enabled == True
            ).to_list()
            
            logger.info(f"   🔍 Found {len(monitors)} monitors watching {symbol}")
            
            alerts_sent = 0
            monitors_triggered = 0
            
            for monitor in monitors:
                monitor_threshold = monitor.crash_threshold
                user_wallet = monitor.userId[:10] + '...'
                
                logger.info(f"   📋 Checking Monitor: {monitor.name}")
                logger.info(f"      👤 User: {user_wallet}")
                logger.info(f"      📉 Threshold: {monitor_threshold}%")
                logger.info(f"      📊 Actual Drop: {price_drop:.2f}%")
                
                # Check if crash meets threshold
                if price_drop >= monitor_threshold:
                    logger.warning(f"      🚨 THRESHOLD EXCEEDED - Sending alerts!")
                    monitors_triggered += 1
                    
                    try:
                        await self._send_comprehensive_alert(monitor, symbol, crash_result)
                        alerts_sent += 1
                        logger.info(f"      ✅ Alerts sent successfully")
                    except Exception as alert_error:
                        logger.error(f"      ❌ Alert sending failed: {alert_error}")
                else:
                    logger.info(f"      ⏭️ Threshold not met - No alert sent")
            
            # Update last alert time
            self.last_alerts[symbol] = datetime.utcnow()
            
            logger.warning(f"🚨 CRASH HANDLING COMPLETE: {symbol}")
            logger.warning(f"   📊 Monitors Checked: {len(monitors)}")
            logger.warning(f"   🚨 Monitors Triggered: {monitors_triggered}")
            logger.warning(f"   📢 Alerts Sent: {alerts_sent}")
            logger.warning(f"   ⏰ Cooldown Set: {self.alert_cooldown/3600:.1f} hours")
                    
        except Exception as e:
            logger.error(f"❌ Error handling crash detection for {symbol}: {e}")
            logger.error(f"   🔍 Error Type: {type(e).__name__}")
            logger.error(f"   📝 Error Details: {str(e)[:200]}...")
            
    async def _send_comprehensive_alert(self, monitor: Monitor, symbol: str, crash_result: Dict):
        """Send comprehensive crash alert with multiple channels"""
        try:
            # Extract ASI analysis
            asi_analysis = crash_result.get("asi_analysis", {})
            analysis_text = "Advanced crash detection algorithms detected significant price movement."
            
            if asi_analysis:
                # Use formatted analysis for better email presentation
                if asi_analysis.get("formatted_analysis", {}).get("email_summary"):
                    analysis_text = asi_analysis["formatted_analysis"]["email_summary"]
                    logger.info(f"🤖 Using formatted ASI analysis for {symbol} alert")
                elif asi_analysis.get("raw_analysis"):
                    # Fallback to raw analysis (truncated)
                    raw_analysis = asi_analysis["raw_analysis"]
                    analysis_text = raw_analysis[:500] + "..." if len(raw_analysis) > 500 else raw_analysis
                    logger.info(f"🤖 Using raw ASI analysis for {symbol} alert (fallback)")
                
                logger.info(f"   📝 Analysis length: {len(analysis_text)} characters")
                logger.info(f"   🎯 ASI Model: {asi_analysis.get('model', 'unknown')}")
                logger.info(f"   ✅ ASI Confidence: {asi_analysis.get('confidence', 'unknown')}")
                logger.info(f"   🎯 Confidence: {asi_analysis.get('confidence', 'unknown')}")
                logger.info(f"   🤖 Model: {asi_analysis.get('model', 'unknown')}")
            else:
                logger.info(f"🤖 No ASI analysis available for {symbol} - using fallback analysis")
            
            # Get token name from symbol
            token_name = self._get_token_name(symbol)
            
            # Calculate price before crash (approximate)
            current_price = crash_result.get("current_price", 0)
            price_drop_percent = abs(crash_result.get("price_drop_24h", 0))
            price_before_crash = current_price / (1 - price_drop_percent / 100) if price_drop_percent > 0 else current_price
            
            # Create comprehensive alert record
            alert = MonitorAlert(
                monitorId=str(monitor.id),
                userId=monitor.userId,  # This is now the wallet address
                symbol=symbol,
                token_name=token_name,
                crash_probability=crash_result.get("crash_probability", 0),
                current_price=current_price,
                price_drop=abs(crash_result.get("price_drop_24h", 0)),
                price_before_crash=price_before_crash,
                analysis=analysis_text,
                crash_detected_at=datetime.utcnow(),
                technical_indicators=crash_result.get("technical_signals", {}),
                asi_analysis=asi_analysis.get("raw_analysis") if asi_analysis else None,
                confidence_level=crash_result.get("confidence_level", "medium"),
                notification_sent=False,
                createdAt=datetime.utcnow()
            )
            
            await alert.insert()
            
            # Get user for notifications by wallet address
            user = await User.find_one(User.walletAddress == monitor.userId)
            if not user:
                logger.error(f"User not found for wallet address {monitor.userId}")
                return
                
            # Send notifications based on channels
            notifications_sent = []
            
            # 1. Telegram notification
            if (user.telegramId and 
                user.notificationPreferences.get("telegram_alerts", True) and
                "telegram" in monitor.notification_channels):
                
                telegram_success = await self._send_telegram_alert(
                    user, monitor, symbol, crash_result, analysis_text
                )
                if telegram_success:
                    notifications_sent.append("telegram")
            
            # 2. Email notification
            if (user.email and 
                user.notificationPreferences.get("email_alerts", False) and
                "email" in monitor.notification_channels):
                
                email_success = await self._send_email_alert(
                    user, monitor, symbol, crash_result, analysis_text
                )
                if email_success:
                    notifications_sent.append("email")
            
            # 3. Log alert (always)
            await self._log_crash_alert(monitor, symbol, crash_result, analysis_text)
            notifications_sent.append("log")
            
            # Update alert with notification status
            alert.notification_sent = len(notifications_sent) > 0
            alert.notification_channels = notifications_sent
            alert.telegram_sent = "telegram" in notifications_sent
            alert.email_sent = "email" in notifications_sent
            alert.webhook_sent = "webhook" in notifications_sent
            await alert.save()
            
            logger.warning(f"🚨 COMPREHENSIVE ALERT SENT:")
            logger.warning(f"   🪙 Token: {alert.token_name} ({symbol})")
            logger.warning(f"   👤 User: {user.username or user.firstName or 'Unknown'}")
            logger.warning(f"   📢 Channels: {', '.join(notifications_sent)}")
            logger.warning(f"   💰 Price: ${crash_result.get('current_price', 0):,.4f}")
            logger.warning(f"   📉 Drop: {abs(crash_result.get('price_drop_24h', 0)):.2f}%")
            logger.warning(f"   🎯 Probability: {crash_result.get('crash_probability', 0):.1f}%")
            logger.warning(f"   🔍 Confidence: {crash_result.get('confidence_level', 'unknown')}")
            logger.warning(f"   📊 Alert ID: {str(alert.id)}")
            logger.warning(f"   ⏰ Timestamp: {datetime.utcnow().strftime('%H:%M:%S')} UTC")
            
        except Exception as e:
            logger.error(f"Error sending comprehensive alert: {e}")
    
    async def _send_telegram_alert(self, user: User, monitor: Monitor, symbol: str, crash_result: Dict, analysis: str) -> bool:
        """Send Telegram crash alert"""
        try:
            # Get token name
            token_name = self._get_token_name(symbol)
            
            # Format analysis for Telegram
            short_analysis = analysis[:200] + "..." if len(analysis) > 200 else analysis
            
            # Calculate price before crash
            current_price = crash_result.get('current_price', 0)
            price_drop_percent = abs(crash_result.get('price_drop_24h', 0))
            price_before = current_price / (1 - price_drop_percent / 100) if price_drop_percent > 0 else current_price
            
            message = f"""
🚨 *CRASH ALERT* 🚨

📊 *Monitor:* {monitor.name}
🪙 *Token:* {token_name} ({symbol})
💸 *Current Price:* ${current_price:,.4f}
📈 *Price Before:* ${price_before:,.4f}
📉 *Drop:* {price_drop_percent:.2f}% (${price_before - current_price:,.4f})
🎯 *Crash Probability:* {crash_result.get('crash_probability', 0):.1%}
🔍 *Confidence:* {crash_result.get('confidence_level', 'medium').title()}
⏰ *Detected:* {datetime.utcnow().strftime('%H:%M:%S UTC')}

🤖 *AI Analysis:*
{short_analysis}

⚠️ *Recommended Actions:*
• Review your {token_name} exposure
• Consider risk management strategies
• Monitor market conditions closely
• Check other correlated assets

👤 *Alert for:* {user.firstName or user.username or 'User'}
🔔 Use /monitors to manage your alerts
            """
            
            from app.routers.telegram_webhook import send_telegram_message_direct
            return await send_telegram_message_direct(str(user.telegramId), message)
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def _send_email_alert(self, user: User, monitor: Monitor, symbol: str, crash_result: Dict, analysis: str) -> bool:
        """Send email crash alert"""
        try:
            token_name = self._get_token_name(symbol)
            return await email_service.send_crash_alert(
                user.email,
                f"{token_name} ({symbol})",
                crash_result.get('current_price', 0),
                abs(crash_result.get('price_drop_24h', 0)),
                analysis,
                user.firstName or user.username
            )
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
    
    async def _log_crash_alert(self, monitor: Monitor, symbol: str, crash_result: Dict, analysis: str):
        """Log crash alert to system logs"""
        try:
            token_name = self._get_token_name(symbol)
            current_price = crash_result.get('current_price', 0)
            price_drop = abs(crash_result.get('price_drop_24h', 0))
            
            log_message = f"""
🚨 CRASH ALERT LOGGED 🚨
Monitor: {monitor.name}
Token: {token_name} ({symbol})
User ID: {monitor.userId}
Current Price: ${current_price:,.4f}
Price Drop: {price_drop:.2f}%
Crash Probability: {crash_result.get('crash_probability', 0):.2%}
Confidence: {crash_result.get('confidence_level', 'medium')}
Technical Indicators: {len(crash_result.get('technical_signals', {}))} signals
ASI Analysis: {'Available' if crash_result.get('asi_analysis') else 'Not available'}
Detection Time: {datetime.utcnow().isoformat()}
Analysis Preview: {analysis[:150]}...
            """
            logger.warning(log_message)
            
        except Exception as e:
            logger.error(f"Error logging crash alert: {e}")
            
    async def add_symbol(self, symbol: str):
        """Add a symbol to monitoring"""
        self.monitored_symbols.add(symbol)
        logger.info(f"Added {symbol} to monitoring")
        
    async def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring"""
        self.monitored_symbols.discard(symbol)
        if symbol in self.price_history:
            del self.price_history[symbol]
        if symbol in self.last_alerts:
            del self.last_alerts[symbol]
        logger.info(f"Removed {symbol} from monitoring")
        
    def _get_token_name(self, symbol: str) -> str:
        """Get human-readable token name from symbol"""
        token_names = {
            "BTCUSDT": "Bitcoin",
            "ETHUSDT": "Ethereum", 
            "BNBUSDT": "Binance Coin",
            "ADAUSDT": "Cardano",
            "SOLUSDT": "Solana",
            "XRPUSDT": "XRP",
            "DOTUSDT": "Polkadot",
            "DOGEUSDT": "Dogecoin",
            "AVAXUSDT": "Avalanche",
            "SHIBUSDT": "Shiba Inu",
            "MATICUSDT": "Polygon",
            "LTCUSDT": "Litecoin",
            "UNIUSDT": "Uniswap",
            "LINKUSDT": "Chainlink",
            "ATOMUSDT": "Cosmos",
            "ETCUSDT": "Ethereum Classic",
            "XLMUSDT": "Stellar",
            "BCHUSDT": "Bitcoin Cash",
            "FILUSDT": "Filecoin",
            "TRXUSDT": "TRON"
        }
        return token_names.get(symbol, symbol.replace("USDT", ""))
    
    def get_status(self) -> Dict:
        """Get enhanced monitoring service status"""
        return {
            "available": True,
            "running": self.is_running,
            "monitored_symbols": len(self.monitored_symbols),
            "symbols": list(self.monitored_symbols),
            "check_interval": self.check_interval,
            "price_history_symbols": len(self.price_history),
            "recent_alerts": len(self.last_alerts),
            "asi_configured": asi_crash_detector.is_configured(),
            "email_configured": email_service.is_configured(),
            "alert_cooldown": self.alert_cooldown
        }

# Global enhanced monitor service instance
enhanced_monitor_service = EnhancedMonitorService()

async def start_monitor_service():
    """Start the enhanced monitor service"""
    await enhanced_monitor_service.start_monitoring()

def stop_monitor_service():
    """Stop the enhanced monitor service"""
    enhanced_monitor_service.stop_monitoring()

def get_monitor_service_status():
    """Get enhanced monitor service status"""
    return enhanced_monitor_service.get_status()
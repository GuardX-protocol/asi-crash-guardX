from datetime import datetime
from uuid import uuid4
import os
import sys
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.services.unified_crash_detector import UnifiedCrashDetector

# ASI Integration for intelligent explanations
try:
    from openai import OpenAI
    ASI_API_KEY = os.getenv('ASI_API_KEY')
    
    if ASI_API_KEY:
        client = OpenAI(base_url='https://api.asi1.ai/v1', api_key=ASI_API_KEY)
        ASI_AVAILABLE = True
        print(f"✅ ASI Model configured")
    else:
        client = None
        ASI_AVAILABLE = False
        print("❌ ASI_API_KEY not found in environment")
        
except ImportError as e:
    client = None
    ASI_AVAILABLE = False
    print(f"❌ OpenAI import failed: {e}")
except Exception as e:
    client = None
    ASI_AVAILABLE = False
    print(f"❌ ASI initialization failed: {e}")

load_dotenv()

# ASI-powered crash detection - no external agent needed

# Create sender agent with mailbox
crash_sentinel = Agent(
    name="crash-sentinel",
    seed=os.getenv('AGENT_SEED', 'crash_sentinel_seed_123'),
    port=8001,
    mailbox=True,  # IMPORTANT: Must have mailbox
    agentverse={
        "mailbox_key": os.getenv("AGENTVERSE_API_KEY")
    }
)

# Protocol for chat
chat_protocol = Protocol(spec=chat_protocol_spec)

# Initialize unified detector (Prophet + ARIMA + Anomaly Detection)
detector = UnifiedCrashDetector()

# ASI-powered standalone crash detection

async def explain_crash_with_asi(ctx: Context, crash_data: dict) -> str:
    """Use ASI to explain detected crash - INTELLIGENT USE CASE"""
    if not ASI_AVAILABLE:
        return f"Crash detected: {crash_data.get('symbol')} - {crash_data.get('crash_probability', 0):.1f}% probability"
    
    try:
        prompt = f"""Crypto crash detected by our algorithms:

Symbol: {crash_data.get('symbol', 'N/A')}
Price: ${crash_data.get('current_price', 0):.4f}
Crash Probability: {crash_data.get('crash_probability', 0):.1f}%
Market Sentiment: {crash_data.get('market_sentiment', 'NEUTRAL')}
Volatility: {crash_data.get('volatility', 0):.4f}
Warning Level: {crash_data.get('warning_level', 'UNKNOWN')}

Provide:
1. Risk level (one word)
2. What's happening (1 sentence)
3. Recommended action (1 sentence)
4. Time horizon

Be concise and actionable."""

        response = client.chat.completions.create(
            model="asi1-fast",
            messages=[
                {"role": "system", "content": "You are GuardX AI, expert crypto crash analyst. Provide clear, actionable advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        ctx.logger.error(f"ASI analysis failed: {e}")
        return f"Crash detected: {crash_data.get('symbol')} - {crash_data.get('crash_probability', 0):.1f}% probability"

async def generate_crash_alert(ctx: Context, crash_data: dict) -> str:
    """Generate comprehensive crash alert with ASI analysis"""
    try:
        # Get ASI explanation for the crash
        asi_explanation = await explain_crash_with_asi(ctx, crash_data)
        
        # Format comprehensive alert
        alert_message = f"""🚨 **GUARDX CRASH ALERT**

**SYMBOL:** {crash_data.get('symbol', 'N/A')}
**CRASH PROBABILITY:** {crash_data.get('crash_probability', 0):.1f}%
**CURRENT PRICE:** ${crash_data.get('current_price', 0):.4f}
**WARNING LEVEL:** {crash_data.get('warning_level', 'UNKNOWN')}

**🤖 ASI ANALYSIS:**
{asi_explanation}

**📊 TECHNICAL DATA:**
• Market Sentiment: {crash_data.get('market_sentiment', 'NEUTRAL')}
• Volatility: {crash_data.get('volatility', 0):.4f}
• Detection Method: Prophet + ARIMA + Anomaly Detection

**📈 TECHNICAL EVIDENCE:**
{format_evidence(crash_data.get('evidence', {}))}

**⏰ DETECTED:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
**🔗 POWERED BY:** GuardX AI + ASI Model"""

        ctx.logger.info(f"✅ Generated comprehensive crash alert for {crash_data.get('symbol')}")
        return alert_message
        
    except Exception as e:
        ctx.logger.error(f"❌ Error generating alert: {e}")
        return f"Crash detected: {crash_data.get('symbol')} - {crash_data.get('crash_probability', 0):.1f}% probability"

def format_evidence(evidence: dict) -> str:
    """Format evidence dictionary for readable display"""
    evidence_items = []
    for key, value in evidence.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                evidence_items.append(f"  {key}.{sub_key}: {sub_value}")
        else:
            evidence_items.append(f"  {key}: {value}")
    return "\n".join(evidence_items[:10])

@chat_protocol.on_message(ChatMessage)
async def handle_user_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle user chat messages with ASI"""
    
    # Send ack
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(),
            acknowledged_msg_id=msg.msg_id
        )
    )
    
    text = msg.text()
    if not text:
        return
    
    # Handle status command
    if text.lower().startswith('/status'):
        symbols_monitored = len(await get_active_monitor_symbols())
        latest_alerts = ctx.storage.get("latest_alerts") or []
        
        status_msg = f"""📊 **GUARDX STATUS**

🔍 Monitoring: {symbols_monitored} symbols
🚨 Recent Alerts: {len(latest_alerts)}
🤖 ASI Model: {'✅ Active' if ASI_AVAILABLE else '❌ Not configured'}
⚡ Detection: Prophet + ARIMA + Anomaly
🕐 Last Scan: {ctx.storage.get('last_scan', 'Never')}

*Ready for intelligent crash detection*"""
        
        await ctx.send(sender, ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=status_msg)]
        ))
        return
    
    # Use ASI for general questions about crypto/markets
    if ASI_AVAILABLE:
        try:
            # Get current monitoring context
            latest_alerts = ctx.storage.get("latest_alerts") or []
            context = ""
            if latest_alerts:
                context = f"\n\nCurrent alerts: {len(latest_alerts)} symbols showing elevated risk"
            
            enhanced_prompt = text + context
            
            response = client.chat.completions.create(
                model="asi1-fast",
                messages=[
                    {"role": "system", "content": "You are GuardX AI, a crypto crash detection expert. Answer questions about crypto markets, risk management, and trading strategies. Be helpful and professional."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            
            await ctx.send(sender, ChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=f"🤖 **GuardX AI**\n\n{answer}")]
            ))
            
        except Exception as e:
            ctx.logger.error(f"ASI chat error: {e}")
            await ctx.send(sender, ChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=[TextContent(type="text", text="Sorry, I'm having trouble processing your question right now. Try /status for system status.")]
            ))

@chat_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    """Handle acknowledgements"""
    ctx.logger.info(f"✅ Message acknowledged by {sender[:20]}")

# Include chat protocol
crash_sentinel.include(chat_protocol)

async def get_active_monitors_with_symbols():
    """Get active monitors with their symbols and user info"""
    try:
        from app.services.fallback_storage import fallback_storage
        
        monitors = await fallback_storage.get_monitors()
        active_monitors = []
        
        for monitor in monitors:
            if monitor.enabled:
                # Ensure symbols have USDT suffix
                symbols = [s + 'USDT' if not s.endswith('USDT') else s for s in monitor.symbols]
                active_monitors.append({
                    'name': monitor.name,
                    'userId': monitor.userId,
                    'symbols': symbols,
                    'crash_probability_threshold': getattr(monitor, 'crash_probability_threshold', 60.0),
                    'telegram_alerts': getattr(monitor, 'telegram_alerts', False),
                    'email_alerts': getattr(monitor, 'email_alerts', False),
                    'alert_webhooks': getattr(monitor, 'alert_webhooks', [])
                })
        
        return active_monitors
    except Exception as e:
        print(f"Error getting active monitors: {e}")
        return []

async def get_active_monitor_symbols():
    """Get symbols from active monitors (backward compatibility)"""
    try:
        monitors = await get_active_monitors_with_symbols()
        symbols = set()
        for monitor in monitors:
            symbols.update(monitor['symbols'])
        
        if not symbols:
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']
        
        return list(symbols)
    except Exception as e:
        print(f"Error getting monitor symbols: {e}")
        return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']

async def get_user_telegram_id(user_id: str):
    """Get user's Telegram ID for notifications"""
    try:
        from app.services.fallback_storage import fallback_storage
        user = await fallback_storage.get_user(user_id)
        return getattr(user, 'telegramId', None) if user else None
    except Exception as e:
        print(f"Error getting user telegram ID: {e}")
        return None

async def send_telegram_notification(telegram_id: str, message: str):
    """Send Telegram notification"""
    try:
        import aiohttp
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token or not telegram_id:
            return False
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                'chat_id': telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            }) as response:
                return response.status == 200
                
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return False

def serialize_for_json(obj):
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, (bool, int, float, str, type(None))):
        return obj
    else:
        return str(obj)  # Convert non-serializable objects to string

async def save_alert_to_storage(alert_data):
    """Save alert to storage with proper JSON serialization"""
    try:
        from app.services.fallback_storage import fallback_storage
        
        # Ensure all data is JSON serializable
        alert_dict = {
            "monitorId": alert_data.get('monitorId', 'crash_sentinel_global'),
            "userId": alert_data.get('userId', 'system'),
            "symbol": alert_data['symbol'],
            "alertType": "crash_detection",
            "crash_probability": float(alert_data['probability']),
            "current_price": float(alert_data.get('current_price', 0)),
            "asi_analysis": str(alert_data.get('agent_analysis', '')),
            "technical_indicators": serialize_for_json(alert_data.get('evidence', {})),
            "severity": str(alert_data.get('severity', 'MEDIUM'))
        }
        
        await fallback_storage.create_alert(alert_dict)
        print(f"✅ Alert saved to storage for {alert_data['symbol']}")
        
    except Exception as e:
        print(f"Failed to save alert: {e}")

@crash_sentinel.on_interval(period=300.0)
async def monitor_and_request_analysis(ctx: Context):
    """Monitor markets based on DB monitors and send notifications"""
    try:
        # Get active monitors from database
        active_monitors = await get_active_monitors_with_symbols()
        
        if not active_monitors:
            ctx.logger.info("📊 No active monitors in database - Agent idle")
            return
        
        # Get all unique symbols to scan
        all_symbols = set()
        for monitor in active_monitors:
            all_symbols.update(monitor['symbols'])
        
        ctx.logger.info(f"🔍 Scanning {len(all_symbols)} symbols from {len(active_monitors)} monitors...")
        
        # Analyze each symbol
        symbol_results = {}
        for symbol in all_symbols:
            try:
                result = await detector.comprehensive_crash_analysis(symbol)
                symbol_results[symbol] = result
            except Exception as e:
                ctx.logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Check each monitor for alerts
        total_alerts = 0
        for monitor in active_monitors:
            try:
                monitor_alerts = []
                
                for symbol in monitor['symbols']:
                    if symbol not in symbol_results:
                        continue
                    
                    result = symbol_results[symbol]
                    crash_prob = result.get('crash_probability', 0)
                    threshold = monitor['crash_probability_threshold']
                    
                    if crash_prob >= threshold:
                        ctx.logger.warning(f"🚨 ALERT: {symbol} - {crash_prob:.1f}% (Monitor: {monitor['name']})")
                        
                        # Prepare crash data
                        crash_data = {
                            'symbol': symbol,
                            'crash_probability': crash_prob,
                            'current_price': result.get('current_price', 0),
                            'market_sentiment': result.get('market_sentiment', 'NEUTRAL'),
                            'volatility': result.get('volatility', 0),
                            'warning_level': result.get('warning_level', 'UNKNOWN'),
                            'evidence': result.get('evidence', {})
                        }
                        
                        # Generate comprehensive alert with ASI analysis
                        alert_message = await generate_crash_alert(ctx, crash_data)
                        
                        # Create alert for storage
                        alert = {
                            'monitorId': monitor['name'],
                            'userId': monitor['userId'],
                            'symbol': symbol,
                            'probability': crash_prob,
                            'warning_level': result.get('warning_level', 'UNKNOWN'),
                            'severity': result.get('severity', 'MEDIUM'),
                            'evidence': result.get('evidence', {}),
                            'agent_analysis': alert_message,
                            'current_price': result.get('current_price', 0),
                            'volatility': result.get('volatility', 0),
                            'market_sentiment': result.get('market_sentiment', 'NEUTRAL'),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        monitor_alerts.append(alert)
                        await save_alert_to_storage(alert)
                        
                        # Send Telegram notification if enabled
                        if monitor['telegram_alerts']:
                            telegram_id = await get_user_telegram_id(monitor['userId'])
                            if telegram_id:
                                # Format Telegram message
                                telegram_msg = f"""🚨 *GUARDX CRASH ALERT*

*Symbol:* {symbol}
*Crash Probability:* {crash_prob:.1f}%
*Price:* ${result.get('current_price', 0):.4f}
*Monitor:* {monitor['name']}

{alert_message[:500]}...

*Time:* {datetime.now().strftime('%H:%M UTC')}"""
                                
                                success = await send_telegram_notification(telegram_id, telegram_msg)
                                if success:
                                    ctx.logger.info(f"📱 Telegram sent to user {monitor['userId'][:8]}")
                                else:
                                    ctx.logger.warning(f"📱 Telegram failed for user {monitor['userId'][:8]}")
                        
                        total_alerts += 1
                
                if monitor_alerts:
                    ctx.logger.info(f"📊 Monitor '{monitor['name']}': {len(monitor_alerts)} alerts generated")
                    
            except Exception as e:
                ctx.logger.error(f"Error processing monitor {monitor['name']}: {e}")
                continue
        
        # Store scan results
        ctx.storage.set("last_scan", datetime.now().isoformat())
        ctx.storage.set("total_monitors_scanned", len(active_monitors))
        ctx.storage.set("total_symbols_scanned", len(all_symbols))
        
        if total_alerts > 0:
            ctx.logger.info(f"📊 Scan complete: {total_alerts} alerts from {len(active_monitors)} monitors")
        else:
            ctx.logger.info(f"📊 Scan complete: No alerts from {len(active_monitors)} monitors")
            
    except Exception as e:
        ctx.logger.error(f"Monitor error: {e}")

@crash_sentinel.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("🚀 GuardX Crash Sentinel Online")
    ctx.logger.info(f"📍 Address: {crash_sentinel.address}")
    ctx.logger.info(f"🤖 ASI Model: {'✅ Active' if ASI_AVAILABLE else '❌ Not configured'}")
    ctx.logger.info("⚡ Detection: Prophet + ARIMA + Anomaly")
    ctx.logger.info("🧠 Analysis: ASI-powered explanations")
    ctx.logger.info("💬 Chat: ASI-powered user support")
    ctx.logger.info("✅ Ready for standalone intelligent crash detection")

# Utility functions for API access
def get_agent():
    return crash_sentinel

def get_latest_alerts():
    return crash_sentinel.storage.get("latest_alerts") or []

def get_latest_agent_response():
    return crash_sentinel.storage.get("latest_agent_response")

def get_pending_requests():
    return {}  # No pending requests in standalone mode

# Legacy function for backward compatibility
async def run_crash_detection(symbol=None, lookback=None):
    """Legacy function for backward compatibility with existing API"""
    if symbol:
        result = await detector.comprehensive_crash_analysis(symbol)
        
        # Add agent analysis if crash probability is significant
        if result.get('crash_probability', 0) > 30:
            try:
                # Try to get cached agent analysis first
                cached_analysis = crash_sentinel.storage.get("latest_agent_response")
                if cached_analysis:
                    result['agent_analysis'] = cached_analysis.get('analysis', 'No analysis available')
                else:
                    result['agent_analysis'] = "Agent analysis will be requested automatically"
                    result['agent_request_sent'] = True
            except Exception as e:
                result['agent_analysis'] = f"Agent communication error: {str(e)}"
        
        return result
    else:
        # Return results for multiple symbols (simplified)
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']
        results = {}
        for sym in symbols[:5]:
            try:
                results[sym] = await detector.comprehensive_crash_analysis(sym)
            except:
                continue
        return results

if __name__ == "__main__":
    crash_sentinel.run()
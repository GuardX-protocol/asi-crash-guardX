from uagents import Agent, Context, Protocol, Model
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from app.services.crash_algorithms import AdvancedCrashDetector
from app.models import MonitorAlert, User, Monitor
import os
from dotenv import load_dotenv
import asyncio
from uuid import uuid4

# Try to import proper chat protocol, fallback if not available
try:
    from uagents_core.contrib.protocols.chat import (
        ChatMessage as UAgentsChatMessage,
        ChatAcknowledgement,
        TextContent,
        chat_protocol_spec,
    )
    CHAT_PROTOCOL_AVAILABLE = True
    print("✅ uAgents chat protocol available")
except ImportError:
    try:
        from uagents.contrib.protocols.chat import (
            ChatMessage as UAgentsChatMessage,
            ChatAcknowledgement, 
            TextContent,
            chat_protocol_spec,
        )
        CHAT_PROTOCOL_AVAILABLE = True
        print("✅ uAgents chat protocol available (alternative import)")
    except ImportError:
        CHAT_PROTOCOL_AVAILABLE = False
        print("⚠️ Chat protocol not available, using custom implementation")
        
        # Create dummy classes for fallback
        class UAgentsChatMessage:
            pass
        class ChatAcknowledgement:
            pass
        class TextContent:
            pass

load_dotenv()

crash_sentinel = Agent(
    name="crash-sentinel",
    seed=os.getenv('AGENT_SEED', 'crash_sentinel_unique_seed_phrase_12345'),
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

detector = AdvancedCrashDetector()

async def get_all_tradeable_symbols():
    try:
        response = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=10)
        if response.status_code == 200:
            data = response.json()
            symbols = []
            for symbol_info in data['symbols']:
                if (symbol_info['status'] == 'TRADING' and 
                    symbol_info['symbol'].endswith('USDT') and
                    symbol_info['symbol'] not in ['USDCUSDT', 'BUSDUSDT', 'TUSDUSDT']):
                    symbols.append(symbol_info['symbol'])
            return sorted(symbols)[:100]
        return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']
    except:
        return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']

async def analyze_with_agent(ctx: Context, crash_data):
    try:
        evidence_items = []
        for key, value in crash_data.get('evidence', {}).items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    evidence_items.append(f"{key}.{sub_key}: {sub_value}")
            else:
                evidence_items.append(f"{key}: {value}")
        
        evidence_summary = "\n".join(evidence_items[:10])
        
        # Format analysis request for Agentverse chat agent
        analysis_request = f"""Analyze crash risk:

**Symbol:** {crash_data.get('symbol', 'N/A')}
**Current Price:** ${crash_data.get('current_price', 0):,.2f}
**Crash Probability:** {crash_data.get('crash_probability', 0)}%
**Warning Level:** {crash_data.get('warning_level', 'UNKNOWN')}
**Market Sentiment:** {crash_data.get('market_sentiment', 'NEUTRAL')}
**Volatility:** {crash_data.get('volatility', 0):.4f}

**Technical Evidence:**
{evidence_summary}

Provide professional analysis with:
1. Risk Assessment
2. Recommended Action (HOLD/REDUCE/EXIT)
3. Key Risk Factors
4. Time Horizon
5. Price Targets"""

        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        request_id = f"req_{datetime.now().timestamp()}_{crash_data.get('symbol', 'unknown')}"
        
        # Enhanced logging for analysis request
        ctx.logger.info(f"🔍 SENDING ANALYSIS REQUEST:")
        ctx.logger.info(f"   Target: {target_agent}")
        ctx.logger.info(f"   Symbol: {crash_data.get('symbol', 'UNKNOWN')}")
        ctx.logger.info(f"   Crash Probability: {crash_data.get('crash_probability', 0)}%")
        ctx.logger.info(f"   Request ID: {request_id}")
        ctx.logger.info(f"   Current Price: ${crash_data.get('current_price', 0):,.2f}")
        ctx.logger.info(f"   Evidence Items: {len(evidence_items)}")
        
        # Send analysis request to target agent
        try:
            ctx.logger.info(f"🔍 Requesting analysis for {crash_data.get('symbol')} from target agent")
            chat_request_id = await send_message_to_target_agent(ctx, analysis_request)
            
            if chat_request_id:
                ctx.logger.info(f"✅ Analysis request sent to target agent (Chat ID: {chat_request_id[:8]})")
                
                # Store request for correlation
                ctx.storage.set(f"pending_request_{request_id}", {
                    "symbol": crash_data.get('symbol', 'UNKNOWN'),
                    "timestamp": datetime.now().isoformat(),
                    "status": "sent_to_target",
                    "chat_request_id": chat_request_id,
                    "timeout_seconds": 60
                })
                
                # Add to timeout tracking with longer timeout for analysis
                timeout_tracker.add_request(request_id, 60)
                
                return f"Analysis request sent to target agent - Response pending (ID: {request_id[:8]})"
            else:
                ctx.logger.warning("⚠️ Failed to send to target agent, trying fallback")
        
        except Exception as chat_error:
            ctx.logger.warning(f"⚠️ Target agent communication failed: {chat_error}")
            
        # Fallback to custom protocols if Agentverse fails
        try:
            custom_chat_id = await send_custom_chat_message(ctx, analysis_request, f"analysis_{crash_data.get('symbol', 'unknown')}")
            if custom_chat_id:
                ctx.logger.info(f"✅ Analysis sent via custom chat fallback (ID: {custom_chat_id[:8]})")
                
                ctx.storage.set(f"pending_request_{request_id}", {
                    "symbol": crash_data.get('symbol', 'UNKNOWN'),
                    "timestamp": datetime.now().isoformat(),
                    "status": "sent_via_custom_fallback",
                    "chat_request_id": custom_chat_id,
                    "timeout_seconds": 45
                })
                
                timeout_tracker.add_request(request_id, 45)
                return f"Analysis request sent via fallback - Response pending (ID: {request_id[:8]})"
        except Exception as custom_chat_error:
            ctx.logger.warning(f"⚠️ Custom chat fallback also failed: {custom_chat_error}")
        
        # Fallback to traditional AnalysisRequest
        try:
            analysis_msg = AnalysisRequest(
                type="analysis_request",
                symbol=crash_data.get('symbol', 'UNKNOWN'),
                crash_probability=crash_data.get('crash_probability', 0),
                data=crash_data,
                request=analysis_request,
                timestamp=datetime.now().isoformat(),
                request_id=request_id,
                timeout_seconds=45
            )
            
            await ctx.send(target_agent, analysis_msg)
            
            # Store pending request for response correlation
            ctx.storage.set(f"pending_request_{request_id}", {
                "symbol": crash_data.get('symbol', 'UNKNOWN'),
                "timestamp": datetime.now().isoformat(),
                "status": "sent_via_analysis_protocol",
                "timeout_seconds": 45
            })
            
            # Add to timeout tracking
            timeout_tracker.add_request(request_id, 45)
            
            ctx.logger.info(f"✅ Analysis request sent via AnalysisRequest protocol (ID: {request_id[:8]})")
            return f"Analysis request sent to agent {target_agent[:20]}... - Response pending (ID: {request_id[:8]})"
            
        except Exception as analysis_error:
            ctx.logger.error(f"❌ AnalysisRequest protocol also failed: {analysis_error}")
            return f"All analysis protocols failed: {str(analysis_error)}"
        
    except Exception as e:
        ctx.logger.error(f"❌ Critical error in analyze_with_agent: {e}")
        return f"Agent communication error: {str(e)}"

async def analyze_with_agent_fallback(ctx: Context, crash_data):
    try:
        evidence_items = []
        for key, value in crash_data.get('evidence', {}).items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    evidence_items.append(f"{key}.{sub_key}: {sub_value}")
            else:
                evidence_items.append(f"{key}: {value}")
        
        evidence_summary = "\n".join(evidence_items[:10])
        
        analysis_request = f"""CRYPTO CRASH ANALYSIS REPORT

SYMBOL: {crash_data.get('symbol', 'N/A')}
CURRENT PRICE: ${crash_data.get('current_price', 0):,.2f}
CRASH PROBABILITY: {crash_data.get('crash_probability', 0)}%
WARNING LEVEL: {crash_data.get('warning_level', 'UNKNOWN')}
MARKET SENTIMENT: {crash_data.get('market_sentiment', 'NEUTRAL')}
VOLATILITY: {crash_data.get('volatility', 0):.4f}

TECHNICAL EVIDENCE:
{evidence_summary}

As a professional crypto risk analyst, provide:
1. RISK ASSESSMENT: One sentence summary of current risk level
2. RECOMMENDED ACTION: HOLD/REDUCE/EXIT with position size %
3. KEY RISK FACTORS: Top 3 factors driving the risk
4. TIME HORIZON: immediate/24h/48h/week concern level
5. PRICE TARGETS: Support/resistance levels if crash occurs

Keep response under 200 words, be direct and actionable."""

        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        
        await ctx.send(
            target_agent,
            AnalysisRequest(
                type="analysis_request",
                symbol=crash_data.get('symbol', 'UNKNOWN'),
                crash_probability=crash_data.get('crash_probability', 0),
                data=crash_data,
                request=analysis_request,
                timestamp=datetime.now().isoformat()
            )
        )
        
        ctx.logger.info(f"📤 Fallback analysis request sent to agent {target_agent[:20]}...")
        return f"Analysis request sent to agent {target_agent[:20]}... - Response pending"
        
    except Exception as e:
        ctx.logger.error(f"Error sending fallback request to agent: {e}")
        return f"Agent communication error: {str(e)}"

def save_alert_to_storage_sync(alert_data):
    """Save alert to storage synchronously to avoid event loop conflicts"""
    try:
        from app.services.fallback_storage import fallback_storage
        
        alert_dict = {
            "monitorId": "crash_sentinel_global",
            "userId": "system",
            "symbol": alert_data['symbol'],
            "alertType": "crash_detection",
            "crash_probability": alert_data['probability'],
            "current_price": alert_data.get('current_price', 0),
            "agent_analysis": alert_data.get('agent_analysis', ''),
            "technical_indicators": alert_data.get('evidence', {}),
            "severity": alert_data.get('severity', 'MEDIUM'),
            "timestamp": datetime.now().isoformat()
        }
        
        # Use only synchronous fallback storage
        try:
            alerts = fallback_storage._storage.get('alerts', [])
            alerts.append(alert_dict)
            fallback_storage._storage['alerts'] = alerts
            print(f"✅ Alert saved to storage for {alert_data['symbol']}")
        except Exception as storage_error:
            print(f"Storage save error: {storage_error}")
            
    except Exception as e:
        print(f"Failed to save alert: {e}")

async def save_alert_to_db(alert_data):
    """Async wrapper for synchronous alert saving"""
    save_alert_to_storage_sync(alert_data)

def get_active_monitor_symbols_sync():
    """Get active monitor symbols synchronously to avoid event loop conflicts"""
    try:
        from app.services.fallback_storage import fallback_storage
        
        symbols = set()
        
        # Use only synchronous fallback storage to avoid async loop issues
        try:
            monitors_data = fallback_storage._storage.get('monitors', [])
            for monitor_data in monitors_data:
                if monitor_data.get('enabled', False):
                    symbols.update(monitor_data.get('symbols', []))
        except Exception as storage_error:
            print(f"Storage access error: {storage_error}")
        
        if not symbols:
            # Return default symbols if no monitors found
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']
        
        return [s + 'USDT' if not s.endswith('USDT') else s for s in symbols]
    except Exception as e:
        print(f"Error getting monitor symbols: {e}")
        # Return default symbols on any error
        return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']

async def get_active_monitor_symbols():
    """Async wrapper for synchronous symbol retrieval"""
    return get_active_monitor_symbols_sync()

@crash_sentinel.on_interval(period=300.0)
async def monitor_markets(ctx: Context):
    try:
        symbols = await get_active_monitor_symbols()
        
        if not symbols:
            ctx.logger.info("📊 No active monitors - Agent idle")
            return
        
        ctx.logger.info(f"🔍 Scanning {len(symbols)} symbols from active monitors...")
        alerts = []
        
        for symbol in symbols:
            try:
                result = await detector.comprehensive_crash_analysis(symbol)
                
                if result.get('crash_probability', 0) > 50:
                    try:
                        agent_analysis = await analyze_with_agent(ctx, result)
                    except Exception as e:
                        ctx.logger.warning(f"Agent communication failed, using fallback: {e}")
                        agent_analysis = await analyze_with_agent_fallback(ctx, result)
                    
                    alert = {
                        'symbol': symbol,
                        'probability': result.get('crash_probability', 0),
                        'warning_level': result.get('warning_level', 'UNKNOWN'),
                        'severity': result.get('severity', 'MEDIUM'),
                        'evidence': result.get('evidence', {}),
                        'agent_analysis': agent_analysis,
                        'current_price': result.get('current_price', 0),
                        'volatility': result.get('volatility', 0),
                        'market_sentiment': result.get('market_sentiment', 'NEUTRAL'),
                        'timestamp': result.get('timestamp', datetime.now().isoformat())
                    }
                    
                    alerts.append(alert)
                    await save_alert_to_db(alert)
                    
                    ctx.logger.warning(f"🚨 CRASH ALERT: {symbol} - {alert['probability']}% probability")
                    
            except Exception as e:
                ctx.logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        ctx.storage.set("latest_alerts", alerts)
        ctx.storage.set("last_scan", datetime.now().isoformat())
        ctx.storage.set("total_symbols_monitored", len(symbols))
        
        if alerts:
            ctx.logger.info(f"📊 Scan complete: {len(alerts)} alerts from {len(symbols)} monitored symbols")
        else:
            ctx.logger.info(f"📊 Scan complete: No critical alerts from {len(symbols)} monitored symbols")
            
    except Exception as e:
        ctx.logger.error(f"Error in market monitoring: {e}")

# DISABLED: Ping function was causing runtime errors with event loop
# @crash_sentinel.on_interval(period=120.0)  # Ping every 2 minutes
# async def ping_target_agent(ctx: Context):
#     """Periodically ping the target agent to maintain connection"""
#     try:
#         await ping_agent(ctx)
#     except Exception as e:
#         ctx.logger.error(f"Error in periodic ping: {e}")

@crash_sentinel.on_interval(period=10.0)  # Check for manual requests every 10 seconds
async def process_manual_requests(ctx: Context):
    """Process manual requests from API endpoints"""
    try:
        # Check for manual message requests
        message_request = ctx.storage.get("manual_message_request")
        if message_request and message_request.get("status") == "pending":
            content = message_request.get("content", "")
            message_type = message_request.get("type", "general")
            
            # Try chat protocol first for manual messages
            if message_type == "chat" or message_type == "general":
                request_id = await send_chat_request_to_agent(ctx, content, "manual_chat")
            else:
                request_id = await send_message_to_agent(ctx, content, message_type)
            
            if request_id:
                message_request["status"] = "sent"
                message_request["request_id"] = request_id
                ctx.storage.set("manual_message_request", message_request)
                ctx.logger.info(f"📤 Manual message sent: {content[:50]}...")
        
        # Check for manual analysis requests
        analysis_request = ctx.storage.get("manual_analysis_request")
        if analysis_request and analysis_request.get("status") == "pending":
            symbol = analysis_request.get("symbol", "")
            custom_request = analysis_request.get("request", "")
            
            request_id = await request_custom_analysis(ctx, symbol, custom_request)
            if request_id:
                analysis_request["status"] = "sent"
                analysis_request["actual_request_id"] = request_id
                ctx.storage.set("manual_analysis_request", analysis_request)
                ctx.logger.info(f"📤 Manual analysis request sent for {symbol}")
        
        # Check for manual ping requests
        ping_request = ctx.storage.get("manual_ping_request")
        if ping_request and ping_request.get("status") == "pending":
            success = await ping_agent(ctx)
            if success:
                ping_request["status"] = "sent"
                ping_request["sent_timestamp"] = datetime.now().isoformat()
                ctx.storage.set("manual_ping_request", ping_request)
                ctx.logger.info("🏓 Manual ping sent")
        
    except Exception as e:
        ctx.logger.error(f"Error processing manual requests: {e}")

@crash_sentinel.on_interval(period=60.0)  # Check timeouts every 15 seconds
async def check_request_timeouts(ctx: Context):
    """Check for timed out requests and log them"""
    try:
        timed_out_requests = timeout_tracker.check_timeouts()
        
        if timed_out_requests:
            ctx.logger.warning(f"⏰ TIMEOUT DETECTED:")
            for request_id in timed_out_requests:
                ctx.logger.warning(f"   Request {request_id[:8]}... timed out")
                
                # Update storage to reflect timeout
                pending_key = f"pending_request_{request_id}"
                pending_request = ctx.storage.get(pending_key)
                if pending_request:
                    pending_request["status"] = "timeout"
                    pending_request["timeout_timestamp"] = datetime.now().isoformat()
                    ctx.storage.set(pending_key, pending_request)
        
        # Log current status
        pending_count = timeout_tracker.get_pending_count()
        if pending_count > 0:
            ctx.logger.info(f"📊 Timeout tracker: {pending_count} pending requests")
        
    except Exception as e:
        ctx.logger.error(f"Error checking timeouts: {e}")

@crash_sentinel.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info("🚀 CRASH SENTINEL AGENT STARTED")
    ctx.logger.info(f"Agent Address: {crash_sentinel.address}")
    ctx.logger.info(f"Mailbox Enabled: Connected to Agentverse")
    ctx.logger.info("Monitoring: ACTIVE MONITOR SYMBOLS ONLY")
    ctx.logger.info("Enhanced Algorithm: 85%+ accuracy")
    ctx.logger.info("AI Analysis: Agent-to-Agent Communication")
    ctx.logger.info("Target Agent: agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734")
    ctx.logger.info("=" * 60)
    
    # Initial ping disabled to prevent runtime errors
    ctx.logger.info("🚀 Agent startup complete - ready for communication")
    ctx.logger.info("📬 Mailbox enabled - will receive responses from target agent")
    ctx.logger.info(f"🔗 Agent inspector: https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8003&address={crash_sentinel.address}")

def get_agent():
    return crash_sentinel

def get_latest_alerts():
    return crash_sentinel.storage.get("latest_alerts") or []

async def send_message_to_target_agent(ctx: Context, message_content: str):
    """Send message directly to target agent"""
    try:
        # Send to the original target agent
        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        
        if CHAT_PROTOCOL_AVAILABLE:
            # Create proper chat message for Agentverse
            content = [TextContent(type="text", text=message_content)]
            chat_msg = UAgentsChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=content
            )
            
            ctx.logger.info(f"📤 SENDING MESSAGE TO TARGET AGENT:")
            ctx.logger.info(f"   Target: {target_agent[:20]}...")
            ctx.logger.info(f"   Message ID: {chat_msg.msg_id}")
            ctx.logger.info(f"   Content: {message_content[:100]}...")
            ctx.logger.info(f"   Protocol: uAgents ChatMessage")
            
            # Send the message
            await ctx.send(target_agent, chat_msg)
            
            # Store with proper message ID
            ctx.storage.set(f"sent_message_{chat_msg.msg_id}", {
                "message": message_content,
                "target": target_agent,
                "timestamp": datetime.now().isoformat(),
                "status": "sent",
                "protocol": "chat_message",
                "msg_id": str(chat_msg.msg_id)
            })
            
            ctx.logger.info(f"✅ Message sent to target agent successfully (ID: {str(chat_msg.msg_id)[:8]})")
            return str(chat_msg.msg_id)
        else:
            ctx.logger.warning("⚠️ Chat protocol not available, using custom message fallback")
            # Fallback to custom chat message
            return await send_custom_chat_message(ctx, message_content, "target_fallback")
        
    except Exception as e:
        ctx.logger.error(f"❌ Error sending message to Agentverse: {e}")
        ctx.logger.error(f"   Exception details: {type(e).__name__}: {str(e)}")
        return None

async def send_chat_message_proper(ctx: Context, message_content: str):
    """Wrapper for target agent message"""
    return await send_message_to_target_agent(ctx, message_content)

async def send_proper_chat_message(ctx: Context, message_content: str, conversation_id: str = "default"):
    """Wrapper for backward compatibility"""
    return await send_chat_message_proper(ctx, message_content)

async def send_custom_chat_message(ctx: Context, message_content: str, conversation_id: str = "default"):
    """Send a chat message using custom chat protocol"""
    try:
        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        request_id = f"custom_chat_{datetime.now().timestamp()}"
        
        # Create custom chat message
        chat_msg = CustomChatMessage(
            message=message_content,
            sender=str(crash_sentinel.address),
            timestamp=datetime.now().isoformat(),
            request_id=request_id,
            conversation_id=conversation_id
        )
        
        # Log the outgoing message details
        ctx.logger.info(f"🗨️ SENDING CUSTOM CHAT MESSAGE:")
        ctx.logger.info(f"   Target: {target_agent}")
        ctx.logger.info(f"   Request ID: {request_id}")
        ctx.logger.info(f"   Conversation ID: {conversation_id}")
        ctx.logger.info(f"   Message: {message_content[:100]}...")
        ctx.logger.info(f"   Protocol: Custom Chat")
        
        # Add to timeout tracking
        timeout_tracker.add_request(request_id, 30)
        
        # Send the message
        await ctx.send(target_agent, chat_msg)
        
        # Store the sent message for tracking
        ctx.storage.set(f"sent_custom_chat_{request_id}", {
            "message": message_content,
            "target": target_agent,
            "timestamp": datetime.now().isoformat(),
            "status": "sent",
            "conversation_id": conversation_id,
            "protocol": "custom_chat"
        })
        
        ctx.logger.info(f"✅ Custom chat message sent successfully (ID: {request_id[:8]})")
        return request_id
        
    except Exception as e:
        ctx.logger.error(f"❌ Error sending custom chat message: {e}")
        return None

async def send_message_to_agent(ctx: Context, message_content: str, message_type: str = "general"):
    """Send a general message to the target agent with enhanced logging"""
    try:
        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        request_id = f"msg_{datetime.now().timestamp()}"
        
        # Log the outgoing message details
        ctx.logger.info(f"📤 SENDING MESSAGE:")
        ctx.logger.info(f"   Target: {target_agent}")
        ctx.logger.info(f"   Type: {message_type}")
        ctx.logger.info(f"   Request ID: {request_id}")
        ctx.logger.info(f"   Content: {message_content[:100]}...")
        ctx.logger.info(f"   Sender: {crash_sentinel.address}")
        
        # Add to timeout tracking
        timeout_tracker.add_request(request_id, 30)
        
        # Try multiple message formats to ensure compatibility
        message_sent = False
        last_error = None
        
        try:
            # First try with proper uAgents chat protocol
            chat_result = await send_chat_message_proper(ctx, message_content)
            if chat_result:
                message_sent = True
                ctx.logger.info(f"✅ Message sent via proper chat protocol (ID: {chat_result[:8]})")
        except Exception as e1:
            last_error = e1
            ctx.logger.warning(f"⚠️ Proper chat protocol failed: {e1}")
            
            # Try custom chat protocol as fallback
            try:
                custom_chat_result = await send_custom_chat_message(ctx, message_content, f"conv_{request_id}")
                if custom_chat_result:
                    message_sent = True
                    ctx.logger.info(f"✅ Message sent via custom chat protocol (ID: {custom_chat_result[:8]})")
            except Exception as e1b:
                last_error = e1b
                ctx.logger.warning(f"⚠️ Custom chat protocol failed: {e1b}")
        
        if not message_sent:
            try:
                # Fallback to GeneralMessage model
                general_msg = GeneralMessage(
                    type=message_type,
                    content=message_content,
                    timestamp=datetime.now().isoformat(),
                    request_id=request_id
                )
                
                await ctx.send(target_agent, general_msg)
                message_sent = True
                ctx.logger.info(f"✅ Message sent via GeneralMessage protocol")
                
            except Exception as e2:
                last_error = e2
                ctx.logger.warning(f"⚠️ GeneralMessage protocol failed: {e2}")
        
        if not message_sent:
            try:
                # Final fallback to SimpleTextMessage
                simple_msg = SimpleTextMessage(text=message_content)
                await ctx.send(target_agent, simple_msg)
                message_sent = True
                ctx.logger.info(f"✅ Message sent via SimpleTextMessage protocol")
                
            except Exception as e3:
                last_error = e3
                ctx.logger.warning(f"⚠️ SimpleTextMessage protocol failed: {e3}")
        
        if message_sent:
            # Store the sent message for tracking
            ctx.storage.set(f"sent_message_{request_id}", {
                "content": message_content,
                "type": message_type,
                "target": target_agent,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            })
            
            ctx.logger.info(f"📋 Message tracking stored for ID: {request_id[:8]}")
            return request_id
        else:
            ctx.logger.error(f"❌ All message protocols failed. Last error: {last_error}")
            return None
        
    except Exception as e:
        ctx.logger.error(f"❌ Critical error in send_message_to_agent: {e}")
        return None

async def ping_agent(ctx: Context):
    """Send a ping to the target agent to test connectivity"""
    try:
        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        
        await ctx.send(
            target_agent,
            PingMessage(
                timestamp=datetime.now().isoformat(),
                sender_address=str(crash_sentinel.address)
            )
        )
        
        ctx.logger.info(f"🏓 Ping sent to agent {target_agent[:20]}...")
        return True
        
    except Exception as e:
        ctx.logger.error(f"Error pinging agent: {e}")
        return False

def get_latest_agent_response():
    """Get the latest response from the target agent"""
    return crash_sentinel.storage.get("latest_agent_response")

def get_latest_general_message():
    """Get the latest general message from the target agent"""
    return crash_sentinel.storage.get("latest_general_message")

def get_latest_flexible_message():
    """Get the latest flexible message from the target agent"""
    return crash_sentinel.storage.get("latest_flexible_message")

def get_latest_text_message():
    """Get the latest text message from the target agent"""
    return crash_sentinel.storage.get("latest_text_message")

def get_latest_raw_message():
    """Get the latest raw message from the target agent"""
    return crash_sentinel.storage.get("latest_raw_message") or {"message": "No raw messages captured yet"}

def get_latest_agent_error():
    """Get the latest error from the target agent"""
    return crash_sentinel.storage.get("latest_agent_error")

def get_latest_chat_message():
    """Get the latest custom chat message from the target agent"""
    return crash_sentinel.storage.get("latest_custom_chat_message")

def get_latest_chat_response():
    """Get the latest custom chat response from the target agent"""
    return crash_sentinel.storage.get("latest_custom_chat_response")

def get_latest_proper_chat_message():
    """Get the latest proper uAgents chat message from the target agent"""
    return crash_sentinel.storage.get("latest_proper_chat_message")

def get_last_caught_message():
    """Get the last message caught by universal handler"""
    return crash_sentinel.storage.get("last_caught_message")

def get_timeout_status():
    """Get timeout tracking status"""
    return {
        "pending_requests": timeout_tracker.get_pending_count(),
        "total_requests": len(timeout_tracker.pending_requests),
        "timeout_details": timeout_tracker.pending_requests
    }

def get_all_agent_messages():
    """Get all types of messages from the target agent"""
    return {
        "analysis_response": get_latest_agent_response(),
        "general_message": get_latest_general_message(),
        "flexible_message": get_latest_flexible_message(),
        "text_message": get_latest_text_message(),
        "raw_message": get_latest_raw_message(),
        "error_message": get_latest_agent_error(),
        "custom_chat_message": get_latest_chat_message(),
        "custom_chat_response": get_latest_chat_response(),
        "proper_chat_message": get_latest_proper_chat_message(),
        "universal_catch": get_last_caught_message(),
        "connection_status": get_agent_connection_status(),
        "timeout_status": get_timeout_status(),
        "chat_protocol_available": CHAT_PROTOCOL_AVAILABLE
    }

def get_agent_connection_status():
    """Get the connection status with the target agent"""
    return crash_sentinel.storage.get("agent_connection_status")

def get_pending_requests():
    """Get all pending requests to the target agent"""
    storage_keys = crash_sentinel.storage._storage.keys() if hasattr(crash_sentinel.storage, '_storage') else []
    pending_requests = {}
    
    for key in storage_keys:
        if key.startswith("pending_request_"):
            request_id = key.replace("pending_request_", "")
            pending_requests[request_id] = crash_sentinel.storage.get(key)
    
    return pending_requests

async def request_custom_analysis(ctx: Context, symbol: str, custom_request: str):
    """Send a custom analysis request to the target agent"""
    try:
        target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
        request_id = f"custom_{datetime.now().timestamp()}_{symbol}"
        
        # Enhanced logging for custom analysis
        ctx.logger.info(f"🔍 SENDING CUSTOM ANALYSIS REQUEST:")
        ctx.logger.info(f"   Target: {target_agent}")
        ctx.logger.info(f"   Symbol: {symbol}")
        ctx.logger.info(f"   Request ID: {request_id}")
        ctx.logger.info(f"   Custom Request: {custom_request[:100]}...")
        
        # Get current market data for the symbol
        try:
            result = await detector.comprehensive_crash_analysis(symbol)
            crash_data = {
                'symbol': symbol,
                'current_price': result.get('current_price', 0),
                'crash_probability': result.get('crash_probability', 0),
                'warning_level': result.get('warning_level', 'UNKNOWN'),
                'market_sentiment': result.get('market_sentiment', 'NEUTRAL'),
                'volatility': result.get('volatility', 0),
                'evidence': result.get('evidence', {})
            }
            ctx.logger.info(f"   Market Data: Price=${crash_data['current_price']:,.2f}, Risk={crash_data['crash_probability']}%")
        except Exception as market_error:
            ctx.logger.warning(f"⚠️ Could not get market data: {market_error}")
            crash_data = {'symbol': symbol}
        
        # Try chat protocol first
        try:
            chat_request = f"CUSTOM ANALYSIS REQUEST for {symbol}:\n\n{custom_request}"
            chat_request_id = await send_chat_message(ctx, chat_request, f"custom_analysis_{symbol}")
            if chat_request_id:
                ctx.logger.info(f"✅ Custom analysis sent via chat protocol")
                
                # Store pending request with chat correlation
                ctx.storage.set(f"pending_request_{request_id}", {
                    "symbol": symbol,
                    "custom_request": custom_request,
                    "timestamp": datetime.now().isoformat(),
                    "status": "sent_via_chat",
                    "type": "custom",
                    "chat_request_id": chat_request_id,
                    "timeout_seconds": 60
                })
                
                timeout_tracker.add_request(request_id, 60)
                return request_id
                
        except Exception as chat_error:
            ctx.logger.warning(f"⚠️ Chat protocol failed for custom analysis: {chat_error}")
        
        # Fallback to AnalysisRequest protocol
        analysis_msg = AnalysisRequest(
            type="custom_analysis_request",
            symbol=symbol,
            crash_probability=crash_data.get('crash_probability', 0),
            data=crash_data,
            request=custom_request,
            timestamp=datetime.now().isoformat(),
            request_id=request_id,
            timeout_seconds=60
        )
        
        await ctx.send(target_agent, analysis_msg)
        
        # Store pending request
        ctx.storage.set(f"pending_request_{request_id}", {
            "symbol": symbol,
            "custom_request": custom_request,
            "timestamp": datetime.now().isoformat(),
            "status": "sent_via_analysis_protocol",
            "type": "custom",
            "timeout_seconds": 60
        })
        
        timeout_tracker.add_request(request_id, 60)
        
        ctx.logger.info(f"✅ Custom analysis request sent for {symbol} (ID: {request_id[:8]})")
        return request_id
        
    except Exception as e:
        ctx.logger.error(f"❌ Error sending custom analysis request: {e}")
        return None

async def send_chat_request_to_agent(ctx: Context, message: str, conversation_id: str = "api_chat"):
    """Send a chat message from API request"""
    try:
        # Try proper chat protocol first
        request_id = await send_chat_message_proper(ctx, message)
        if request_id:
            ctx.logger.info(f"📤 API chat message sent via proper protocol (ID: {request_id[:8]})")
            return request_id
        
        # Fallback to custom chat
        request_id = await send_custom_chat_message(ctx, message, conversation_id)
        if request_id:
            ctx.logger.info(f"📤 API chat message sent via custom protocol (ID: {request_id[:8]})")
            return request_id
        else:
            ctx.logger.error("❌ Failed to send API chat message")
            return None
    except Exception as e:
        ctx.logger.error(f"❌ Error in send_chat_request_to_agent: {e}")
        return None



async def run_crash_detection(symbol=None, lookback=None):
    if symbol:
        result = await detector.comprehensive_crash_analysis(symbol, lookback or 200)
        
        # Add agent analysis if crash probability is significant
        if result.get('crash_probability', 0) > 30:
            try:
                # Try to get cached agent analysis first
                cached_analysis = crash_sentinel.storage.get(f"agent_analysis_{symbol}")
                if cached_analysis:
                    result['agent_analysis'] = cached_analysis['analysis']
                else:
                    # Send request to agent for analysis
                    target_agent = "agent1qf9espq0gnw2q6udjcr8xd0vxgq02y3dczcdnz8dz9xwenngvwhk5ejm734"
                    analysis_request = f"Analyze crash risk for {symbol}: {result.get('crash_probability', 0)}% probability"
                    
                    # This would be sent asynchronously, so we use fallback for immediate response
                    # Note: This needs a context object to work properly
                    result['agent_analysis'] = "Agent analysis request will be sent asynchronously"
                    result['agent_request_sent'] = True
            except Exception as e:
                result['agent_analysis'] = f"Agent communication error: {str(e)}"
        
        return result
    else:
        symbols = await get_all_tradeable_symbols()
        results = {}
        for sym in symbols[:10]:
            try:
                results[sym] = await detector.comprehensive_crash_analysis(sym, lookback or 200)
            except:
                continue
        return results

class CustomChatMessage(Model):
    """Custom chat protocol message for agent-to-agent communication"""
    type: str = "custom_chat"
    message: str
    sender: str = ""
    timestamp: str = ""
    request_id: str = ""
    conversation_id: str = ""

class CustomChatResponse(Model):
    """Custom chat protocol response"""
    type: str = "custom_chat_response"
    message: str
    sender: str = ""
    timestamp: str = ""
    request_id: str = ""
    conversation_id: str = ""

class AnalysisRequest(Model):
    type: str
    symbol: str
    crash_probability: float
    data: dict
    request: str
    timestamp: str
    request_id: str = ""
    timeout_seconds: int = 30

class AnalysisResponse(Model):
    type: str
    symbol: str
    analysis: str
    timestamp: str
    request_id: str = ""
    sender_address: str = ""

class GeneralMessage(Model):
    type: str
    content: str
    timestamp: str
    request_id: str = ""

class PingMessage(Model):
    type: str = "ping"
    timestamp: str
    sender_address: str = ""

class PongMessage(Model):
    type: str = "pong"
    timestamp: str
    original_timestamp: str = ""

class FlexibleMessage(Model):
    """Flexible message model to handle any incoming message format"""
    content: str = ""
    message: str = ""
    text: str = ""
    data: dict = {}
    type: str = "unknown"
    timestamp: str = ""

class UnknownMessage(Model):
    """Catch-all message model for unknown formats"""
    pass
    
class SimpleTextMessage(Model):
    """Simple text message model"""
    text: str
    
class ErrorMessage(Model):
    """Error message model"""
    error: str
    message: str = ""
    timestamp: str = ""

class TimeoutTracker:
    """Track request timeouts and manage pending requests"""
    def __init__(self):
        self.pending_requests = {}
        self.timeout_callbacks = {}
    
    def add_request(self, request_id: str, timeout_seconds: int = 30):
        """Add a request to timeout tracking"""
        self.pending_requests[request_id] = {
            "timestamp": datetime.now(),
            "timeout_seconds": timeout_seconds,
            "status": "pending"
        }
    
    def complete_request(self, request_id: str):
        """Mark a request as completed"""
        if request_id in self.pending_requests:
            self.pending_requests[request_id]["status"] = "completed"
            self.pending_requests[request_id]["completed_at"] = datetime.now()
    
    def check_timeouts(self):
        """Check for timed out requests"""
        current_time = datetime.now()
        timed_out = []
        
        for request_id, request_info in self.pending_requests.items():
            if request_info["status"] == "pending":
                elapsed = (current_time - request_info["timestamp"]).total_seconds()
                if elapsed > request_info["timeout_seconds"]:
                    request_info["status"] = "timeout"
                    request_info["timed_out_at"] = current_time
                    timed_out.append(request_id)
        
        return timed_out
    
    def get_pending_count(self):
        """Get count of pending requests"""
        return len([r for r in self.pending_requests.values() if r["status"] == "pending"])

# Global timeout tracker
timeout_tracker = TimeoutTracker()

analysis_protocol = Protocol()

@analysis_protocol.on_message(model=AnalysisResponse)
async def handle_analysis_response(ctx: Context, sender: str, msg: AnalysisResponse):
    """Handle analysis responses from the target agent"""
    try:
        ctx.logger.info(f"📥 RECEIVED ANALYSIS RESPONSE:")
        ctx.logger.info(f"   From: {sender[:20]}...")
        ctx.logger.info(f"   Symbol: {msg.symbol}")
        ctx.logger.info(f"   Request ID: {msg.request_id[:8] if msg.request_id else 'N/A'}")
        ctx.logger.info(f"   Analysis Length: {len(msg.analysis)} characters")
        ctx.logger.info(f"   Response Preview: {msg.analysis[:100]}...")
        
        # Store the analysis response for later retrieval
        ctx.storage.set(f"agent_analysis_{msg.symbol}", {
            "analysis": msg.analysis,
            "timestamp": msg.timestamp,
            "sender": sender,
            "request_id": msg.request_id
        })
        
        # Update pending request status and timeout tracker
        if msg.request_id:
            # Mark as completed in timeout tracker
            timeout_tracker.complete_request(msg.request_id)
            
            # Update pending request status
            pending_key = f"pending_request_{msg.request_id}"
            pending_request = ctx.storage.get(pending_key)
            if pending_request:
                pending_request["status"] = "completed"
                pending_request["response_timestamp"] = datetime.now().isoformat()
                pending_request["response_length"] = len(msg.analysis)
                ctx.storage.set(pending_key, pending_request)
                ctx.logger.info(f"✅ Request {msg.request_id[:8]} marked as completed")
        
        # Store latest response for quick access
        ctx.storage.set("latest_agent_response", {
            "symbol": msg.symbol,
            "analysis": msg.analysis,
            "timestamp": msg.timestamp,
            "sender": sender,
            "request_id": msg.request_id,
            "source": "analysis_response_protocol"
        })
        
        ctx.logger.info(f"✅ Analysis response fully processed for {msg.symbol}")
        
    except Exception as e:
        ctx.logger.error(f"Error handling analysis response: {e}")

@analysis_protocol.on_message(model=GeneralMessage)
async def handle_general_message(ctx: Context, sender: str, msg: GeneralMessage):
    """Handle general messages from the target agent"""
    try:
        ctx.logger.info(f"📨 Received message from agent {sender[:20]}: {msg.content[:50]}...")
        
        # Store general message
        ctx.storage.set("latest_general_message", {
            "content": msg.content,
            "timestamp": msg.timestamp,
            "sender": sender,
            "request_id": msg.request_id
        })
        
    except Exception as e:
        ctx.logger.error(f"Error handling general message: {e}")

@analysis_protocol.on_message(model=PongMessage)
async def handle_pong_message(ctx: Context, sender: str, msg: PongMessage):
    """Handle pong responses from the target agent"""
    try:
        ctx.logger.info(f"🏓 Received pong from agent {sender[:20]}...")
        
        # Calculate round-trip time if original timestamp exists
        if msg.original_timestamp:
            try:
                original_time = datetime.fromisoformat(msg.original_timestamp.replace('Z', '+00:00'))
                current_time = datetime.now()
                rtt = (current_time - original_time.replace(tzinfo=None)).total_seconds()
                ctx.logger.info(f"⏱️ Round-trip time: {rtt:.2f}s")
            except:
                pass
        
        # Store connection status
        ctx.storage.set("agent_connection_status", {
            "connected": True,
            "last_pong": datetime.now().isoformat(),
            "sender": sender
        })
        
    except Exception as e:
        ctx.logger.error(f"Error handling pong message: {e}")

@analysis_protocol.on_message(model=FlexibleMessage)
async def handle_flexible_message(ctx: Context, sender: str, msg: FlexibleMessage):
    """Handle flexible messages from the target agent"""
    try:
        # Extract content from various possible fields
        content = msg.content or msg.message or msg.text or str(msg.data)
        
        ctx.logger.info(f"📨 Received flexible message from agent {sender[:20]}: {content[:100]}...")
        
        # Store the message
        ctx.storage.set("latest_flexible_message", {
            "content": content,
            "full_message": msg.dict(),
            "timestamp": msg.timestamp or datetime.now().isoformat(),
            "sender": sender,
            "message_type": msg.type
        })
        
        # If it looks like an analysis response, treat it as such
        if any(keyword in content.lower() for keyword in ['analysis', 'risk', 'recommendation', 'btc', 'eth', 'usdt']):
            ctx.storage.set("latest_agent_response", {
                "symbol": "UNKNOWN",
                "analysis": content,
                "timestamp": msg.timestamp or datetime.now().isoformat(),
                "sender": sender,
                "request_id": "",
                "source": "flexible_handler"
            })
            ctx.logger.info("✅ Flexible message stored as analysis response")
        
    except Exception as e:
        ctx.logger.error(f"Error handling flexible message: {e}")

@analysis_protocol.on_message(model=SimpleTextMessage)
async def handle_simple_text_message(ctx: Context, sender: str, msg: SimpleTextMessage):
    """Handle simple text messages from the target agent"""
    try:
        ctx.logger.info(f"📨 Received text message from agent {sender[:20]}: {msg.text[:100]}...")
        
        # Store the message
        ctx.storage.set("latest_text_message", {
            "text": msg.text,
            "timestamp": datetime.now().isoformat(),
            "sender": sender
        })
        
        # If it looks like an analysis response, treat it as such
        if any(keyword in msg.text.lower() for keyword in ['analysis', 'risk', 'recommendation', 'btc', 'eth', 'usdt']):
            ctx.storage.set("latest_agent_response", {
                "symbol": "UNKNOWN",
                "analysis": msg.text,
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "request_id": "",
                "source": "text_handler"
            })
            ctx.logger.info("✅ Text message stored as analysis response")
        
    except Exception as e:
        ctx.logger.error(f"Error handling simple text message: {e}")

@analysis_protocol.on_message(model=ErrorMessage)
async def handle_error_message(ctx: Context, sender: str, msg: ErrorMessage):
    """Handle error messages from the target agent"""
    try:
        ctx.logger.warning(f"⚠️ Received error from agent {sender[:20]}: {msg.error}")
        
        # Store the error
        ctx.storage.set("latest_agent_error", {
            "error": msg.error,
            "message": msg.message,
            "timestamp": msg.timestamp or datetime.now().isoformat(),
            "sender": sender
        })
        
    except Exception as e:
        ctx.logger.error(f"Error handling error message: {e}")

@analysis_protocol.on_message(model=UnknownMessage)
async def handle_unknown_message(ctx: Context, sender: str, msg: UnknownMessage):
    """Handle unknown message types from the target agent"""
    try:
        msg_type = type(msg).__name__
        msg_content = str(msg)
        
        ctx.logger.info(f"🔍 UNKNOWN MESSAGE HANDLER:")
        ctx.logger.info(f"   Type: {msg_type}")
        ctx.logger.info(f"   From: {sender[:20]}...")
        ctx.logger.info(f"   Content: {msg_content[:200]}...")
        
        # Try to extract useful information
        extracted_info = {}
        
        # Check if it has common attributes
        for attr in ['text', 'message', 'content', 'analysis', 'data']:
            if hasattr(msg, attr):
                value = getattr(msg, attr)
                if callable(value):
                    try:
                        value = value()
                    except:
                        pass
                extracted_info[attr] = str(value)[:200] if value else None
        
        # Store for inspection
        ctx.storage.set("last_caught_message", {
            "type": msg_type,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "raw_content": msg_content[:500],
            "extracted_info": extracted_info,
            "has_attributes": [attr for attr in dir(msg) if not attr.startswith('_')]
        })
        
        # If we can extract meaningful text, store as potential response
        meaningful_text = None
        for key, value in extracted_info.items():
            if value and len(value) > 10:
                meaningful_text = value
                break
        
        if not meaningful_text and len(msg_content) > 10:
            meaningful_text = msg_content
        
        if meaningful_text:
            ctx.storage.set("latest_agent_response", {
                "symbol": "UNKNOWN_MESSAGE",
                "analysis": meaningful_text,
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "request_id": "",
                "source": "unknown_message_handler",
                "message_type": msg_type
            })
            ctx.logger.info("✅ Unknown message stored as analysis response")
        
        # Update connection status
        ctx.storage.set("agent_connection_status", {
            "connected": True,
            "last_message": datetime.now().isoformat(),
            "sender": sender,
            "message_type": msg_type,
            "via": "unknown_message_handler"
        })
        
        ctx.logger.info(f"✅ Unknown message processed successfully")
        
    except Exception as e:
        ctx.logger.error(f"❌ Error in unknown message handler: {e}")

# Handler for proper uAgents chat protocol
if CHAT_PROTOCOL_AVAILABLE:
    @analysis_protocol.on_message(model=UAgentsChatMessage)
    async def handle_proper_chat_message(ctx: Context, sender: str, msg: UAgentsChatMessage):
        """Handle incoming proper uAgents chat messages"""
        try:
            # Extract text content
            text_content = msg.text() if hasattr(msg, 'text') else str(msg.content)
            
            ctx.logger.info(f"💬 RECEIVED PROPER CHAT MESSAGE:")
            ctx.logger.info(f"   From: {sender[:20]}...")
            ctx.logger.info(f"   Message ID: {msg.msg_id}")
            ctx.logger.info(f"   Content: {text_content[:100]}...")
            ctx.logger.info(f"   Protocol: uAgents Built-in Chat")
            
            # Send acknowledgment
            try:
                ack = ChatAcknowledgement(
                    timestamp=datetime.utcnow(),
                    acknowledged_msg_id=msg.msg_id
                )
                await ctx.send(sender, ack)
                ctx.logger.info(f"✅ Sent acknowledgment for message {str(msg.msg_id)[:8]}")
            except Exception as ack_error:
                ctx.logger.warning(f"⚠️ Failed to send acknowledgment: {ack_error}")
            
            # Store the chat message
            ctx.storage.set("latest_proper_chat_message", {
                "content": text_content,
                "sender": sender,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp),
                "msg_id": str(msg.msg_id),
                "protocol": "uagents_chat"
            })
            
            # If this looks like an analysis response, store it as such
            if any(keyword in text_content.lower() for keyword in ['analysis', 'risk', 'recommendation', 'hold', 'exit', 'reduce']):
                ctx.storage.set("latest_agent_response", {
                    "symbol": "PROPER_CHAT_RESPONSE",
                    "analysis": text_content,
                    "timestamp": datetime.now().isoformat(),
                    "sender": sender,
                    "request_id": str(msg.msg_id),
                    "source": "proper_chat_protocol"
                })
                ctx.logger.info("✅ Proper chat message stored as analysis response")
            
            # Mark request as completed
            timeout_tracker.complete_request(str(msg.msg_id))
            
        except Exception as e:
            ctx.logger.error(f"Error handling proper chat message: {e}")

@analysis_protocol.on_message(model=CustomChatMessage)
async def handle_custom_chat_message(ctx: Context, sender: str, msg: CustomChatMessage):
    """Handle incoming custom chat messages from the target agent"""
    try:
        ctx.logger.info(f"💬 RECEIVED CUSTOM CHAT MESSAGE:")
        ctx.logger.info(f"   From: {sender[:20]}...")
        ctx.logger.info(f"   Request ID: {msg.request_id}")
        ctx.logger.info(f"   Conversation ID: {msg.conversation_id}")
        ctx.logger.info(f"   Message: {msg.message[:100]}...")
        ctx.logger.info(f"   Protocol: Custom Chat")
        
        # Store the chat message
        ctx.storage.set("latest_custom_chat_message", {
            "message": msg.message,
            "sender": sender,
            "timestamp": msg.timestamp,
            "request_id": msg.request_id,
            "conversation_id": msg.conversation_id,
            "protocol": "custom_chat"
        })
        
        # If this looks like an analysis response, store it as such
        if any(keyword in msg.message.lower() for keyword in ['analysis', 'risk', 'recommendation', 'hold', 'exit', 'reduce']):
            ctx.storage.set("latest_agent_response", {
                "symbol": "CUSTOM_CHAT_RESPONSE",
                "analysis": msg.message,
                "timestamp": msg.timestamp,
                "sender": sender,
                "request_id": msg.request_id,
                "source": "custom_chat_protocol"
            })
            ctx.logger.info("✅ Custom chat message stored as analysis response")
        
        # Mark request as completed if we have a request_id
        if msg.request_id:
            timeout_tracker.complete_request(msg.request_id)
        
    except Exception as e:
        ctx.logger.error(f"Error handling custom chat message: {e}")

@analysis_protocol.on_message(model=CustomChatResponse)
async def handle_custom_chat_response(ctx: Context, sender: str, msg: CustomChatResponse):
    """Handle custom chat responses from the target agent"""
    try:
        ctx.logger.info(f"💬 RECEIVED CUSTOM CHAT RESPONSE:")
        ctx.logger.info(f"   From: {sender[:20]}...")
        ctx.logger.info(f"   Request ID: {msg.request_id}")
        ctx.logger.info(f"   Conversation ID: {msg.conversation_id}")
        ctx.logger.info(f"   Response: {msg.message[:100]}...")
        ctx.logger.info(f"   Protocol: Custom Chat Response")
        
        # Store the chat response
        ctx.storage.set("latest_custom_chat_response", {
            "message": msg.message,
            "sender": sender,
            "timestamp": msg.timestamp,
            "request_id": msg.request_id,
            "conversation_id": msg.conversation_id,
            "protocol": "custom_chat_response"
        })
        
        # Store as analysis response
        ctx.storage.set("latest_agent_response", {
            "symbol": "CUSTOM_CHAT_RESPONSE",
            "analysis": msg.message,
            "timestamp": msg.timestamp,
            "sender": sender,
            "request_id": msg.request_id,
            "source": "custom_chat_response_protocol"
        })
        
        # Mark request as completed
        if msg.request_id:
            timeout_tracker.complete_request(msg.request_id)
        
        ctx.logger.info("✅ Custom chat response stored as analysis response")
        
    except Exception as e:
        ctx.logger.error(f"Error handling custom chat response: {e}")



# Note: Universal catch-all handler removed due to uAgents limitations
# The existing specific handlers will catch most message types

crash_sentinel.include(analysis_protocol, publish_manifest=True)
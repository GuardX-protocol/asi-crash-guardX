from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import aiohttp
from datetime import datetime

router = APIRouter()

class TelegramMessage(BaseModel):
    telegram_id: str
    message: str
    parse_mode: str = "Markdown"

class TelegramResponse(BaseModel):
    success: bool
    message: str
    timestamp: str

class WebhookSetup(BaseModel):
    webhook_url: str
    secret_token: Optional[str] = None

class WebhookUpdate(BaseModel):
    webhook_url: Optional[str] = None
    secret_token: Optional[str] = None
    enabled: Optional[bool] = None

@router.post("/send", response_model=TelegramResponse)
async def send_telegram_message(telegram_msg: TelegramMessage):
    """Send a Telegram message to a specific chat ID"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            raise HTTPException(
                status_code=500, 
                detail="TELEGRAM_BOT_TOKEN not configured in environment"
            )
        
        if not telegram_msg.telegram_id:
            raise HTTPException(
                status_code=400, 
                detail="telegram_id is required"
            )
        
        if not telegram_msg.message:
            raise HTTPException(
                status_code=400, 
                detail="message is required"
            )
        
        # Send message via Telegram Bot API
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        
        payload = {
            'chat_id': telegram_msg.telegram_id,
            'text': telegram_msg.message,
            'parse_mode': telegram_msg.parse_mode
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return TelegramResponse(
                        success=True,
                        message=f"Message sent successfully to {telegram_msg.telegram_id}",
                        timestamp=datetime.now().isoformat()
                    )
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Telegram API error: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send Telegram message: {str(e)}"
        )

@router.post("/test")
async def test_telegram_bot():
    """Test if Telegram bot is configured correctly"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            return {
                "configured": False,
                "message": "TELEGRAM_BOT_TOKEN not found in environment"
            }
        
        # Test bot token by getting bot info
        url = f'https://api.telegram.org/bot{bot_token}/getMe'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    bot_info = await response.json()
                    return {
                        "configured": True,
                        "bot_info": bot_info.get('result', {}),
                        "message": "Telegram bot is configured and working"
                    }
                else:
                    return {
                        "configured": False,
                        "message": f"Invalid bot token or API error: {response.status}"
                    }
                    
    except Exception as e:
        return {
            "configured": False,
            "message": f"Error testing bot: {str(e)}"
        }

@router.get("/status")
async def get_telegram_status():
    """Get Telegram integration status"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Get current webhook info
    webhook_info = None
    if bot_token:
        try:
            url = f'https://api.telegram.org/bot{bot_token}/getWebhookInfo'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        webhook_info = data.get('result', {})
        except:
            pass
    
    return {
        "telegram_configured": bool(bot_token),
        "bot_token_present": bool(bot_token),
        "webhook_info": webhook_info,
        "api_endpoint": "https://api.telegram.org/bot<TOKEN>/sendMessage",
        "supported_parse_modes": ["Markdown", "HTML", None]
    }

@router.post("/webhook/setup")
async def setup_webhook(webhook_setup: WebhookSetup):
    """Setup Telegram webhook"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            raise HTTPException(
                status_code=500,
                detail="TELEGRAM_BOT_TOKEN not configured"
            )
        
        url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
        
        payload = {
            'url': webhook_setup.webhook_url,
            'allowed_updates': ['message', 'edited_message', 'callback_query']
        }
        
        if webhook_setup.secret_token:
            payload['secret_token'] = webhook_setup.secret_token
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "message": "Webhook setup successfully",
                        "webhook_url": webhook_setup.webhook_url,
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Telegram API error: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup webhook: {str(e)}"
        )

@router.patch("/webhook")
async def update_webhook(webhook_update: WebhookUpdate):
    """Update Telegram webhook settings"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            raise HTTPException(
                status_code=500,
                detail="TELEGRAM_BOT_TOKEN not configured"
            )
        
        # If disabling webhook
        if webhook_update.enabled is False:
            url = f'https://api.telegram.org/bot{bot_token}/deleteWebhook'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Webhook disabled successfully"
                        }
                    else:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Telegram API error: {error_text}"
                        )
        
        # If updating webhook URL
        elif webhook_update.webhook_url:
            url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
            
            payload = {
                'url': webhook_update.webhook_url,
                'allowed_updates': ['message', 'edited_message', 'callback_query']
            }
            
            if webhook_update.secret_token:
                payload['secret_token'] = webhook_update.secret_token
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "message": "Webhook updated successfully",
                            "webhook_url": webhook_update.webhook_url,
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Telegram API error: {error_text}"
                        )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="No valid update parameters provided"
            )
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update webhook: {str(e)}"
        )

@router.delete("/webhook")
async def delete_webhook():
    """Delete/disable Telegram webhook"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            raise HTTPException(
                status_code=500,
                detail="TELEGRAM_BOT_TOKEN not configured"
            )
        
        url = f'https://api.telegram.org/bot{bot_token}/deleteWebhook'
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "message": "Webhook deleted successfully"
                    }
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Telegram API error: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete webhook: {str(e)}"
        )

class AlertMessage(BaseModel):
    user_id: str  # wallet address or telegram_id
    symbol: str
    alert_type: str
    crash_probability: Optional[float] = None
    price_change: Optional[float] = None
    current_price: float
    severity: str = "medium"
    additional_info: Optional[str] = None

@router.post("/send-alert")
async def send_crash_alert(alert: AlertMessage):
    """Send a crash alert to a user via Telegram"""
    try:
        from app.models import User
        from app.database import is_connected
        
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Find user by wallet address or telegram ID
        user = await User.find_one(User.walletAddress == alert.user_id)
        if not user:
            user = await User.find_one(User.telegramId == alert.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        telegram_id = getattr(user, 'telegramId', None)
        if not telegram_id:
            raise HTTPException(status_code=400, detail="User has no Telegram ID configured")
        
        # Check if user has telegram alerts enabled
        prefs = getattr(user, 'notificationPreferences', {})
        if not prefs.get('telegram_alerts', False):
            return {
                "success": False,
                "message": "User has Telegram alerts disabled",
                "telegram_id": telegram_id
            }
        
        # Format alert message based on severity
        severity_emoji = {
            "high": "🚨",
            "medium": "⚠️", 
            "low": "ℹ️"
        }
        
        emoji = severity_emoji.get(alert.severity.lower(), "⚠️")
        severity_text = alert.severity.upper()
        
        # Build alert message (escape special characters for Markdown)
        def escape_markdown(text):
            """Escape special Markdown characters"""
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text
        
        symbol_escaped = escape_markdown(alert.symbol)
        alert_type_escaped = escape_markdown(alert.alert_type)
        
        alert_message = f"""{emoji} *{severity_text} RISK ALERT*

🪙 *Symbol:* {symbol_escaped}
💰 *Current Price:* ${alert.current_price:,.4f}"""
        
        if alert.crash_probability:
            alert_message += f"\n📊 *Crash Probability:* {alert.crash_probability:.1f}%"
        
        if alert.price_change:
            change_emoji = "📉" if alert.price_change < 0 else "📈"
            alert_message += f"\n{change_emoji} *Price Change:* {alert.price_change:+.2f}%"
        
        alert_message += f"\n🔔 *Alert Type:* {alert_type_escaped}"
        
        if alert.additional_info:
            info_escaped = escape_markdown(alert.additional_info)
            alert_message += f"\n\n💡 *Analysis:*\n{info_escaped}"
        
        alert_message += f"\n\n🕐 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        alert_message += f"\n\n📱 Reply 'disable alerts' to stop notifications"
        
        # Send the alert
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                'chat_id': telegram_id,
                'text': alert_message,
                'parse_mode': 'Markdown'
            }) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "message": f"Alert sent successfully to {telegram_id}",
                        "alert_type": alert.alert_type,
                        "symbol": alert.symbol,
                        "severity": alert.severity,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Telegram API error: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send alert: {str(e)}"
        )

@router.get("/users-with-alerts")
async def get_users_with_telegram_alerts():
    """Get all users who have Telegram alerts enabled"""
    try:
        from app.models import User
        from app.database import ensure_connection
        
        # Ensure database connection
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database not available")
        
        users_with_alerts = []
        
        # Use MongoDB with proper error handling
        users = await User.find_all().to_list()
        for user in users:
            prefs = getattr(user, 'notificationPreferences', {})
            if prefs.get('telegram_alerts', False) and getattr(user, 'telegramId', None):
                users_with_alerts.append({
                    "wallet_address": user.walletAddress,
                    "telegram_id": user.telegramId,
                    "username": getattr(user, 'username', None),
                    "first_name": getattr(user, 'firstName', None),
                    "is_active": getattr(user, 'isActive', True)
                })
        
        return {
            "total_users": len(users_with_alerts),
            "users": users_with_alerts,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get users: {str(e)}"
        )

@router.post("/polling/restart")
async def restart_telegram_polling():
    """Restart Telegram polling service"""
    try:
        from app.services.telegram_polling import stop_telegram_polling, start_telegram_polling
        
        # Stop current polling
        stop_telegram_polling()
        
        # Wait a moment
        import asyncio
        await asyncio.sleep(1)
        
        # Start polling again
        await start_telegram_polling()
        
        return {
            "success": True,
            "message": "Telegram polling service restarted",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart polling: {str(e)}"
        )

@router.post("/webhook/remove")
async def remove_telegram_webhook():
    """Remove Telegram webhook to fix polling conflicts"""
    try:
        from app.services.telegram_polling import telegram_poller
        
        # Remove webhook
        await telegram_poller._remove_webhook()
        
        # Get webhook info to confirm removal
        webhook_info = await telegram_poller.get_webhook_info()
        
        return {
            "success": True,
            "message": "Webhook removal attempted",
            "webhook_info": webhook_info,
            "has_webhook": bool(webhook_info and webhook_info.get('url')),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove webhook: {str(e)}"
        )
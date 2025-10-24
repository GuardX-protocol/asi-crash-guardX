"""
Telegram Polling Service
Automatically polls Telegram for updates and forwards them to the webhook handler
"""

import asyncio
import aiohttp
import logging
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramPollingService:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = 'http://localhost:8000/telegram/webhook'
        self.offset = 0
        self.running = False
        self.poll_interval = 2  # seconds
        self.timeout = 10  # seconds for long polling
        
    async def get_updates(self) -> list:
        """Get updates from Telegram API"""
        if not self.bot_token:
            return []
            
        url = f'https://api.telegram.org/bot{self.bot_token}/getUpdates'
        params = {
            'offset': self.offset,
            'timeout': self.timeout,
            'allowed_updates': ['message', 'edited_message', 'callback_query']
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', [])
                    else:
                        logger.warning(f"Telegram API error: {response.status}")
                        return []
        except asyncio.TimeoutError:
            # Timeout is expected with long polling
            return []
        except Exception as e:
            logger.error(f"Error getting Telegram updates: {e}")
            return []
    
    async def forward_update_to_webhook(self, update: dict) -> bool:
        """Forward update to local webhook handler"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=update,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.warning(f"Webhook error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error forwarding to webhook: {e}")
            return False
    
    async def process_updates(self, updates: list):
        """Process received updates"""
        for update in updates:
            try:
                update_id = update.get('update_id')
                
                # Log the update for debugging
                if 'message' in update:
                    msg = update['message']
                    user = msg.get('from', {})
                    text = msg.get('text', '')
                    logger.info(f"📨 Telegram update {update_id}: {user.get('first_name', 'Unknown')} sent '{text}'")
                
                # Forward to webhook
                success = await self.forward_update_to_webhook(update)
                
                if success:
                    # Update offset to mark this update as processed
                    self.offset = update_id + 1
                else:
                    logger.warning(f"Failed to process update {update_id}")
                    
            except Exception as e:
                logger.error(f"Error processing update: {e}")
    
    async def start_polling(self):
        """Start the polling loop"""
        if not self.bot_token:
            logger.warning("🔕 Telegram polling disabled: TELEGRAM_BOT_TOKEN not configured")
            return
        
        logger.info("📱 Starting Telegram polling service...")
        logger.info(f"🔗 Bot token: {self.bot_token[:10]}...")
        logger.info(f"📡 Polling interval: {self.poll_interval}s")
        
        self.running = True
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while self.running:
                try:
                    updates = await self.get_updates()
                    
                    if updates:
                        logger.info(f"📬 Received {len(updates)} Telegram update(s)")
                        await self.process_updates(updates)
                        consecutive_errors = 0  # Reset error counter on success
                    
                    # Small delay between polls (only if no updates received)
                    if not updates:
                        await asyncio.sleep(self.poll_interval)
                        
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Polling error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive errors, stopping Telegram polling")
                        break
                    
                    # Exponential backoff on errors
                    await asyncio.sleep(min(self.poll_interval * (2 ** consecutive_errors), 60))
                    
        except asyncio.CancelledError:
            logger.info("📱 Telegram polling cancelled")
        except Exception as e:
            logger.error(f"Fatal polling error: {e}")
        finally:
            self.running = False
            logger.info("📱 Telegram polling stopped")
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.running = False
    
    def is_running(self) -> bool:
        """Check if polling is active"""
        return self.running

# Global instance
telegram_poller = TelegramPollingService()

async def start_telegram_polling():
    """Start Telegram polling in background"""
    if telegram_poller.bot_token:
        # Run polling in background task
        asyncio.create_task(telegram_poller.start_polling())
        logger.info("✅ Telegram polling service started")
    else:
        logger.warning("⚠️  Telegram polling not started: Bot token not configured")

def stop_telegram_polling():
    """Stop Telegram polling"""
    telegram_poller.stop_polling()
    logger.info("🛑 Telegram polling service stopped")

def get_polling_status() -> dict:
    """Get current polling status"""
    return {
        "running": telegram_poller.is_running(),
        "bot_token_configured": bool(telegram_poller.bot_token),
        "current_offset": telegram_poller.offset,
        "webhook_url": telegram_poller.webhook_url
    }
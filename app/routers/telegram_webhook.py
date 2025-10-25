from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import asyncio
import re
from datetime import datetime
from app.database import is_connected
from app.models import User

router = APIRouter()

# In-memory user state storage (for production, use Redis or database)
user_states = {}

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None

class TelegramUser(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None

async def set_user_state(telegram_id: str, state: str, data: Dict[str, Any] = None):
    """Set user state for multi-step interactions"""
    user_states[telegram_id] = {
        'state': state,
        'data': data or {},
        'timestamp': datetime.utcnow()
    }

async def get_user_state(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get user state"""
    return user_states.get(telegram_id)

async def clear_user_state(telegram_id: str):
    """Clear user state"""
    if telegram_id in user_states:
        del user_states[telegram_id]

def validate_wallet_address(address: str) -> bool:
    """Validate if the provided string looks like a valid wallet address"""
    address = address.strip()
    
    # Ethereum/EVM addresses (0x followed by 40 hex characters)
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return True
    
    # Bitcoin addresses (various formats)
    if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', address):  # Legacy
        return True
    if re.match(r'^bc1[a-z0-9]{39,59}$', address):  # Bech32
        return True
    
    # Solana addresses (base58, typically 32-44 characters)
    if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return True
    
    # TON addresses (various formats)
    if re.match(r'^[0-9a-fA-F]{48}$', address):  # Raw format
        return True
    if re.match(r'^[a-zA-Z0-9_-]{48}$', address):  # Base64 format
        return True
    
    # Generic crypto address (at least 26 characters, alphanumeric)
    if len(address) >= 26 and re.match(r'^[a-zA-Z0-9]+$', address):
        return True
    
    return False

def get_wallet_type(address: str) -> str:
    """Determine wallet type from address"""
    address = address.strip()
    
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return "Ethereum/EVM"
    elif re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return "Bitcoin (Legacy)"
    elif re.match(r'^bc1[a-z0-9]{39,59}$', address):
        return "Bitcoin (Bech32)"
    elif re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return "Solana"
    elif re.match(r'^[0-9a-fA-F]{48}$', address):
        return "TON (Raw)"
    elif re.match(r'^[a-zA-Z0-9_-]{48}$', address):
        return "TON (Base64)"
    else:
        return "Generic Crypto"

async def store_user_interaction(telegram_id: str, username: str, first_name: str, last_name: str, language_code: str):
    """Store or update user data on any Telegram interaction"""
    try:
        if not is_connected():
            print(f"⚠️ Database not available - cannot store user interaction for {telegram_id}")
            return
        
        # Check if user already exists
        existing_user = await User.find_one(User.telegramId == telegram_id)
        
        if existing_user:
            # Update existing user with latest info and interaction timestamp
            update_data = {
                'username': username,
                'firstName': first_name,
                'lastName': last_name,
                'languageCode': language_code,
                'lastLoginAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow(),
                'isActive': True
            }
            
            # Only update notification preferences if they don't exist
            if not hasattr(existing_user, 'notificationPreferences') or not existing_user.notificationPreferences:
                update_data['notificationPreferences'] = {
                    'telegram_alerts': True,
                    'email_alerts': False,
                    'webhook_alerts': False
                }
            
            await existing_user.update({"$set": update_data})
            print(f"✅ Updated user interaction: {telegram_id} (@{username})")
            
        else:
            # Create new user with temporary wallet address
            temp_wallet = f"tg_{username}_{telegram_id}" if username else f"tg_user_{telegram_id}"
            
            user_data = {
                'walletAddress': temp_wallet,
                'telegramId': telegram_id,
                'username': username,
                'firstName': first_name,
                'lastName': last_name,
                'languageCode': language_code,
                'email': None,
                'isActive': True,
                'notificationPreferences': {
                    'telegram_alerts': True,
                    'email_alerts': False,
                    'webhook_alerts': False
                },
                'monitors': [],
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow(),
                'lastLoginAt': datetime.utcnow()
            }
            
            new_user = User(**user_data)
            await new_user.insert()
            print(f"✅ Created new user from interaction: {telegram_id} (@{username}) -> {temp_wallet}")
            
    except Exception as e:
        print(f"❌ Error storing user interaction: {e}")

async def check_and_prompt_wallet_setup(telegram_id: str, first_name: str):
    """Check if user has a temporary wallet and prompt for real wallet setup"""
    try:
        if not is_connected():
            return
        
        user = await User.find_one(User.telegramId == telegram_id)
        if not user:
            return
        
        # Check if user has a temporary wallet address
        if user.walletAddress and user.walletAddress.startswith('tg_'):
            # Only prompt occasionally (not on every message)
            import random
            if random.random() < 0.1:  # 10% chance to prompt
                prompt_message = f"""💡 Hi {first_name}! 

You're using a temporary wallet address: `{user.walletAddress}`

🔗 Want to connect your real wallet for better security?
• Send your MetaMask address (0x...)
• Or send your Telegram wallet address
• Or send /wallet to update anytime

This helps secure your account and monitors! ✨"""
                
                await send_telegram_message_direct(telegram_id, prompt_message)
                print(f"💡 Prompted user {telegram_id} for wallet setup")
        
    except Exception as e:
        print(f"❌ Error checking wallet setup: {e}")

@router.post("/webhook")
async def telegram_webhook(update: TelegramUpdate):
    """Handle incoming Telegram updates"""
    try:
        if not is_connected():
            return {"ok": False, "error": "Database not available"}
        
        # Handle regular messages
        if update.message:
            await handle_message(update.message)
        
        # Handle edited messages
        elif update.edited_message:
            await handle_message(update.edited_message)
        
        # Handle callback queries (inline buttons)
        elif update.callback_query:
            await handle_callback_query(update.callback_query)
        
        return {"ok": True}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}

async def handle_message(message: Dict[str, Any]):
    """Handle incoming Telegram messages"""
    try:
        # Extract user info
        user_data = message.get('from', {})
        chat_data = message.get('chat', {})
        text = message.get('text', '')
        
        telegram_id = str(user_data.get('id', ''))
        username = user_data.get('username')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        language_code = user_data.get('language_code', 'en')
        
        if not telegram_id:
            return
        
        # Automatically store/update user data on any interaction
        await store_user_interaction(telegram_id, username, first_name, last_name, language_code)
        
        # Check if user needs wallet setup (only for non-command messages)
        if not text.startswith('/') and not await get_user_state(telegram_id):
            await check_and_prompt_wallet_setup(telegram_id, first_name)
        
        # Handle /start command
        if text.startswith('/start'):
            await handle_start_command(telegram_id, username, first_name, last_name, language_code)
        
        # Handle other commands
        elif text.startswith('/help'):
            await send_help_message(telegram_id)
        
        elif text.startswith('/status'):
            await send_status_message(telegram_id)
        
        elif text.startswith('/settings'):
            await send_settings_message(telegram_id)
        
        elif text.startswith('/report'):
            await handle_report_message(telegram_id, text)
        
        elif text.startswith('/wallet'):
            await handle_wallet_command(telegram_id, username, first_name, last_name, language_code)
        
        else:
            # Handle regular messages
            await handle_regular_message(telegram_id, text)
            
    except Exception as e:
        print(f"Message handling error: {e}")

async def handle_start_command(telegram_id: str, username: str, first_name: str, last_name: str, language_code: str):
    """Handle /start command - register or update user"""
    try:
        if not is_connected():
            await send_telegram_message_direct(telegram_id, "❌ Service temporarily unavailable. Please try again later.")
            return
        
        # Check if user already exists
        existing_user = await User.find_one(User.telegramId == telegram_id)
        
        if existing_user:
            # Check if user has a real wallet address or temporary one
            has_real_wallet = existing_user.walletAddress and not existing_user.walletAddress.startswith('tg_')
            
            # Update existing user with latest info
            update_data = {
                'telegramId': telegram_id,
                'username': username,
                'firstName': first_name,
                'lastName': last_name,
                'languageCode': language_code,
                'lastLoginAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow(),
                'isActive': True,  # Reactivate user
                'notificationPreferences': {
                    **getattr(existing_user, 'notificationPreferences', {}),
                    'telegram_alerts': True  # Enable telegram alerts by default
                }
            }
            
            # Update in MongoDB
            await existing_user.update({"$set": update_data})
            updated_user = await User.find_one(User.telegramId == telegram_id)
            
            # Get user's current monitors for status
            from app.models import Monitor
            monitors = await Monitor.find(Monitor.userId == existing_user.walletAddress).to_list()
            active_monitors = len([m for m in monitors if m.enabled])
            
            if has_real_wallet:
                welcome_message = f"""👋 Welcome back, {first_name}!

🎯 Your GuardX account is reconnected:
✅ Telegram ID: `{telegram_id}`
✅ Username: @{username or 'Not set'}
✅ Wallet: `{existing_user.walletAddress}`
📊 Active Monitors: {active_monitors}

🔔 Telegram alerts are now ENABLED
You'll receive crash alerts here when your monitors detect high-risk situations.

Type /status for detailed account info or /help for commands."""
            else:
                welcome_message = f"""👋 Welcome back, {first_name}!

⚠️ Your account needs a wallet address update:
✅ Telegram ID: `{telegram_id}`
✅ Username: @{username or 'Not set'}
❌ Wallet: Temporary address `{existing_user.walletAddress}`

🔗 Please send your wallet address to complete setup:
• Send your MetaMask address (0x...)
• Or send your Telegram wallet address
• Or type 'skip' to use temporary address

Example: `0x1234567890abcdef1234567890abcdef12345678`"""
            
        else:
            # New user - ask for wallet address
            welcome_message = f"""🎉 Welcome to GuardX, {first_name}!

🚀 Let's set up your account for crypto crash alerts!

🔗 Please send your wallet address:
• MetaMask address (0x...)
• Telegram wallet address  
• Or any crypto wallet address you want to monitor

📝 Example: `0x1234567890abcdef1234567890abcdef12345678`

💡 This will be used to:
• Identify your account
• Link your monitors and alerts
• Secure your data

⏭️ Or type 'skip' to use a temporary address for now"""
        
        # Send welcome message
        await send_telegram_message_direct(telegram_id, welcome_message)
        
        # Set user state for wallet collection if new user or needs wallet update
        if not existing_user or not (existing_user.walletAddress and not existing_user.walletAddress.startswith('tg_')):
            await set_user_state(telegram_id, 'awaiting_wallet', {
                'username': username,
                'firstName': first_name,
                'lastName': last_name,
                'languageCode': language_code,
                'isNewUser': not existing_user
            })
        
        # Log successful registration/update
        print(f"✅ User interaction: {telegram_id} (@{username}) - {'Existing user' if existing_user else 'New user'}")
        
    except Exception as e:
        print(f"❌ Start command error: {e}")
        await send_telegram_message_direct(telegram_id, "❌ Error setting up your account. Please try again later or contact support.")

async def handle_regular_message(telegram_id: str, text: str):
    """Handle regular text messages"""
    try:
        text_lower = text.lower().strip()
        
        # Check if user is in a state (waiting for wallet address)
        user_state = await get_user_state(telegram_id)
        
        if user_state and user_state['state'] == 'awaiting_wallet':
            await handle_wallet_input(telegram_id, text, user_state['data'])
            return
        
        elif user_state and user_state['state'] == 'updating_wallet':
            await handle_wallet_update(telegram_id, text, user_state['data'])
            return
        
        # Handle alert preferences
        if 'enable alerts' in text_lower or 'turn on alerts' in text_lower:
            await toggle_user_alerts(telegram_id, True)
            return
        
        elif 'disable alerts' in text_lower or 'turn off alerts' in text_lower:
            await toggle_user_alerts(telegram_id, False)
            return
        
        # Simple auto-responses
        elif any(word in text_lower for word in ['hello', 'hi', 'hey']):
            response = "👋 Hello! I'm your GuardX crash detection bot. Type /help for available commands."
        
        elif any(word in text_lower for word in ['help', 'commands']):
            await send_help_message(telegram_id)
            return
        
        elif any(word in text_lower for word in ['status', 'info']):
            await send_status_message(telegram_id)
            return
        
        elif any(word in text_lower for word in ['settings', 'preferences']):
            await send_settings_message(telegram_id)
            return
        
        elif any(word in text_lower for word in ['thanks', 'thank you']):
            response = "🙏 You're welcome! I'm here to help keep your crypto investments safe."
        
        elif any(word in text_lower for word in ['test', 'testing']):
            response = "🧪 Test received! Your bot connection is working perfectly. You'll receive alerts here when monitors detect risks."
        
        else:
            response = """🤖 I received your message! Here's what I can help with:

📱 *Quick Commands:*
• "enable alerts" - Turn on notifications
• "disable alerts" - Turn off notifications  
• "status" - Check your account
• "help" - Show all commands

Type /help for the full command list!"""
        
        await send_telegram_message_direct(telegram_id, response)
        
    except Exception as e:
        print(f"Regular message error: {e}")

async def handle_wallet_input(telegram_id: str, wallet_input: str, user_data: Dict[str, Any]):
    """Handle wallet address input from user"""
    try:
        wallet_input = wallet_input.strip()
        
        # Check if user wants to skip
        if wallet_input.lower() in ['skip', 'skip for now', 'later', 'temp']:
            await create_user_with_temp_wallet(telegram_id, user_data)
            await clear_user_state(telegram_id)
            return
        
        # Validate wallet address
        if not validate_wallet_address(wallet_input):
            error_message = """❌ Invalid wallet address format.

Please send a valid wallet address:
• Ethereum: 0x1234567890abcdef1234567890abcdef12345678
• Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
• Solana: 11111111111111111111111111111112
• TON: EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t

Or type 'skip' to use a temporary address."""
            
            await send_telegram_message_direct(telegram_id, error_message)
            return
        
        # Check if wallet address already exists
        existing_user_with_wallet = await User.find_one(User.walletAddress == wallet_input)
        
        if existing_user_with_wallet and existing_user_with_wallet.telegramId != telegram_id:
            error_message = f"""❌ This wallet address is already registered to another account.

Please use a different wallet address or contact support if this is your wallet.

Wallet: `{wallet_input[:10]}...{wallet_input[-6:]}`"""
            
            await send_telegram_message_direct(telegram_id, error_message)
            return
        
        # Create or update user with real wallet address
        await create_or_update_user_with_wallet(telegram_id, wallet_input, user_data)
        await clear_user_state(telegram_id)
        
    except Exception as e:
        print(f"Wallet input error: {e}")
        await send_telegram_message_direct(telegram_id, "❌ Error processing wallet address. Please try again or type 'skip'.")

async def create_user_with_temp_wallet(telegram_id: str, user_data: Dict[str, Any]):
    """Create user with temporary wallet address"""
    try:
        username = user_data.get('username')
        temp_wallet = f"tg_{username}_{telegram_id}" if username else f"tg_user_{telegram_id}"
        
        user_create_data = {
            'walletAddress': temp_wallet,
            'telegramId': telegram_id,
            'username': username,
            'firstName': user_data.get('firstName'),
            'lastName': user_data.get('lastName'),
            'languageCode': user_data.get('languageCode', 'en'),
            'email': None,
            'isActive': True,
            'notificationPreferences': {
                'telegram_alerts': True,
                'email_alerts': False,
                'webhook_alerts': False
            },
            'lastLoginAt': datetime.utcnow(),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        new_user = User(**user_create_data)
        await new_user.insert()
        
        message = f"""✅ Account created with temporary address!

👤 *Account Details:*
• Name: {user_data.get('firstName', 'User')}
• Telegram ID: `{telegram_id}`
• Wallet: `{temp_wallet}` (temporary)

⚠️ *Important:* You can update to your real wallet address anytime by sending /wallet.

🔔 Telegram alerts are ENABLED
🚀 You can now create monitors and receive crash alerts!

Type /help for available commands."""
        
        await send_telegram_message_direct(telegram_id, message)
        print(f"✅ User created with temp wallet: {telegram_id} -> {temp_wallet}")
        
    except Exception as e:
        print(f"Temp wallet creation error: {e}")
        await send_telegram_message_direct(telegram_id, "❌ Error creating account. Please try /start again.")

async def create_or_update_user_with_wallet(telegram_id: str, wallet_address: str, user_data: Dict[str, Any]):
    """Create new user or update existing user with real wallet address"""
    try:
        wallet_type = get_wallet_type(wallet_address)
        
        # Check if this is an update to existing user
        existing_user = await User.find_one(User.telegramId == telegram_id)
        
        if existing_user:
            # Update existing user's wallet address
            update_data = {
                'walletAddress': wallet_address,
                'username': user_data.get('username'),
                'firstName': user_data.get('firstName'),
                'lastName': user_data.get('lastName'),
                'languageCode': user_data.get('languageCode', 'en'),
                'lastLoginAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow(),
                'isActive': True,
                'notificationPreferences': {
                    **getattr(existing_user, 'notificationPreferences', {}),
                    'telegram_alerts': True
                }
            }
            
            await existing_user.update({"$set": update_data})
            
            message = f"""✅ Wallet address updated successfully!

👤 *Account Details:*
• Name: {user_data.get('firstName', 'User')}
• Telegram ID: `{telegram_id}`
• Wallet: `{wallet_address}`
• Type: {wallet_type}

🔔 Telegram alerts are ENABLED
🚀 You can now create monitors and receive crash alerts!

Type /status to see your account details."""
            
        else:
            # Create new user
            user_create_data = {
                'walletAddress': wallet_address,
                'telegramId': telegram_id,
                'username': user_data.get('username'),
                'firstName': user_data.get('firstName'),
                'lastName': user_data.get('lastName'),
                'languageCode': user_data.get('languageCode', 'en'),
                'email': None,
                'isActive': True,
                'notificationPreferences': {
                    'telegram_alerts': True,
                    'email_alerts': False,
                    'webhook_alerts': False
                },
                'lastLoginAt': datetime.utcnow(),
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }
            
            new_user = User(**user_create_data)
            await new_user.insert()
            
            message = f"""🎉 Welcome to GuardX, {user_data.get('firstName', 'User')}!

✅ *Account Created:*
• Name: {user_data.get('firstName', 'User')}
• Telegram ID: `{telegram_id}`
• Wallet: `{wallet_address}`
• Type: {wallet_type}

🔔 Telegram alerts are ENABLED
🚀 Next steps:
1. Create monitors via our web app
2. Set crash probability thresholds
3. Receive instant alerts here!

📱 Commands:
/status - Check account & monitors
/help - Show all commands
/settings - Manage preferences"""
        
        await send_telegram_message_direct(telegram_id, message)
        
        # Send confirmation
        await asyncio.sleep(1)
        await send_telegram_message_direct(telegram_id, "🚨 Alert system is now active! You'll be notified of any crash risks detected by your monitors.")
        
        print(f"✅ User {'updated' if existing_user else 'created'} with real wallet: {telegram_id} -> {wallet_address}")
        
    except Exception as e:
        print(f"Wallet user creation error: {e}")
        await send_telegram_message_direct(telegram_id, "❌ Error setting up account with wallet address. Please try again.")

async def send_telegram_message_direct(telegram_id: str, message: str):
    """Send message directly via Telegram API"""
    try:
        import aiohttp
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
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
        print(f"Direct message error: {e}")
        return False

# Placeholder functions for other handlers
async def send_help_message(telegram_id: str):
    """Send help message"""
    help_text = """🤖 *GuardX Bot Commands*

/start - Register or update your account
/wallet - Update your wallet address
/help - Show this help message  
/status - Check your account & monitor status
/settings - Manage notification preferences

🔔 *Alert System*
You'll automatically receive alerts when crash risks are detected.

💬 *Text Commands*
• "enable alerts" - Turn on notifications
• "disable alerts" - Turn off notifications"""
    
    await send_telegram_message_direct(telegram_id, help_text)

async def send_status_message(telegram_id: str):
    """Send status message"""
    if not is_connected():
        await send_telegram_message_direct(telegram_id, "❌ Service temporarily unavailable.")
        return
    
    user = await User.find_one(User.telegramId == telegram_id)
    if not user:
        await send_telegram_message_direct(telegram_id, "❌ Account not found. Please send /start to register.")
        return
    
    message = f"""📊 *Your GuardX Status*

👤 *Account:*
• Wallet: `{user.walletAddress}`
• Alerts: {'✅ Enabled' if user.notificationPreferences.get('telegram_alerts', False) else '❌ Disabled'}

Type /help for more commands."""
    
    await send_telegram_message_direct(telegram_id, message)

async def send_settings_message(telegram_id: str):
    """Send settings message"""
    await send_telegram_message_direct(telegram_id, "⚙️ Settings: Use /wallet to update your wallet address or send 'enable alerts'/'disable alerts' to toggle notifications.")

async def handle_report_message(telegram_id: str, text: str):
    """Handle report message"""
    await send_telegram_message_direct(telegram_id, "📝 Thank you for your report! Our team will review it.")

async def handle_wallet_command(telegram_id: str, username: str, first_name: str, last_name: str, language_code: str):
    """Handle wallet command"""
    if not is_connected():
        await send_telegram_message_direct(telegram_id, "❌ Service temporarily unavailable.")
        return
    
    await send_telegram_message_direct(telegram_id, "🔗 Please send your new wallet address or type 'cancel' to abort.")
    await set_user_state(telegram_id, 'updating_wallet', {
        'username': username,
        'firstName': first_name,
        'lastName': last_name,
        'languageCode': language_code
    })

async def handle_wallet_update(telegram_id: str, wallet_input: str, user_data: Dict[str, Any]):
    """Handle wallet update"""
    if wallet_input.lower() == 'cancel':
        await clear_user_state(telegram_id)
        await send_telegram_message_direct(telegram_id, "✅ Wallet update cancelled.")
        return
    
    # Use the same validation and update logic as wallet input
    await handle_wallet_input(telegram_id, wallet_input, user_data)

async def toggle_user_alerts(telegram_id: str, enable: bool):
    """Toggle user alerts"""
    if not is_connected():
        await send_telegram_message_direct(telegram_id, "❌ Service temporarily unavailable.")
        return
    
    user = await User.find_one(User.telegramId == telegram_id)
    if not user:
        await send_telegram_message_direct(telegram_id, "❌ Account not found. Please send /start to register.")
        return
    
    current_prefs = getattr(user, 'notificationPreferences', {})
    current_prefs['telegram_alerts'] = enable
    
    await user.update({"$set": {
        'notificationPreferences': current_prefs,
        'updatedAt': datetime.utcnow()
    }})
    
    status = "ENABLED ✅" if enable else "DISABLED ❌"
    message = f"🔔 Telegram Alerts {status}"
    await send_telegram_message_direct(telegram_id, message)

async def handle_callback_query(callback_query: Dict[str, Any]):
    """Handle callback queries"""
    try:
        # Extract user info from callback query
        user_data = callback_query.get('from', {})
        
        telegram_id = str(user_data.get('id', ''))
        username = user_data.get('username')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        language_code = user_data.get('language_code', 'en')
        
        if telegram_id:
            # Store user interaction data
            await store_user_interaction(telegram_id, username, first_name, last_name, language_code)
        
        # Handle callback data here if needed
        callback_data = callback_query.get('data', '')
        print(f"📞 Callback query from {telegram_id}: {callback_data}")
        
    except Exception as e:
        print(f"Callback query error: {e}")
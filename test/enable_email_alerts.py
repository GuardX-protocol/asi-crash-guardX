#!/usr/bin/env python3
"""
Enable email alerts for a user (for testing purposes)
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import connect_to_mongo
from app.models import User

# Load environment variables
load_dotenv()

async def enable_email_alerts_for_user(wallet_address: str, email: str = None):
    """Enable email alerts for a specific user"""
    
    print(f"🔧 ENABLING EMAIL ALERTS")
    print("=" * 40)
    
    try:
        # Initialize database
        await connect_to_mongo()
        print(f"✅ Database connected")
        
        # Find user by wallet address
        user = await User.find_one(User.walletAddress == wallet_address)
        
        if not user:
            print(f"❌ User not found: {wallet_address}")
            return False
        
        print(f"👤 Found user: {user.firstName or user.username or 'Unknown'}")
        print(f"   Wallet: {user.walletAddress}")
        print(f"   Current Email: {user.email or 'Not set'}")
        
        # Update email if provided
        if email:
            user.email = email
            print(f"   📧 Email updated to: {email}")
        
        # Enable email alerts
        if not user.notificationPreferences:
            user.notificationPreferences = {}
        
        user.notificationPreferences["email_alerts"] = True
        
        # Save changes
        await user.save()
        
        print(f"✅ Email alerts enabled for {user.walletAddress}")
        print(f"   📧 Email: {user.email}")
        print(f"   🔔 Telegram alerts: {user.notificationPreferences.get('telegram_alerts', False)}")
        print(f"   📧 Email alerts: {user.notificationPreferences.get('email_alerts', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def list_users():
    """List all users and their notification settings"""
    
    print(f"👥 USER LIST & NOTIFICATION SETTINGS")
    print("=" * 50)
    
    try:
        await connect_to_mongo()
        
        users = await User.find_all().to_list()
        
        if not users:
            print("❌ No users found")
            return
        
        print(f"Found {len(users)} users:")
        print()
        
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.firstName or user.username or 'Unknown'}")
            print(f"   Wallet: {user.walletAddress}")
            print(f"   Email: {user.email or 'Not set'}")
            print(f"   Telegram ID: {user.telegramId or 'Not set'}")
            print(f"   Notifications:")
            print(f"     📱 Telegram: {user.notificationPreferences.get('telegram_alerts', False)}")
            print(f"     📧 Email: {user.notificationPreferences.get('email_alerts', False)}")
            print(f"   Created: {user.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage user email alert settings")
    parser.add_argument("--list", action="store_true", help="List all users")
    parser.add_argument("--wallet", type=str, help="Wallet address to enable email alerts for")
    parser.add_argument("--email", type=str, help="Email address to set (optional)")
    
    args = parser.parse_args()
    
    if args.list:
        await list_users()
    elif args.wallet:
        success = await enable_email_alerts_for_user(args.wallet, args.email)
        if success:
            print("\n🎯 Email alerts are now enabled!")
            print("   The user will receive email notifications for crash alerts")
            print("   Make sure their monitors include 'email' in notification_channels")
        else:
            print("\n❌ Failed to enable email alerts")
    else:
        print("Usage:")
        print("  python test/enable_email_alerts.py --list")
        print("  python test/enable_email_alerts.py --wallet 0x123... --email user@example.com")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Check Monitor Alerts in Database
===============================

This script checks:
1. If there are any active monitors
2. If there are any alerts stored in the database
3. Monitor service status
4. Recent monitoring activity
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import connect_to_mongo
from app.models import User, Monitor, MonitorAlert

# Load environment variables
load_dotenv()

async def check_monitor_alerts():
    """Check monitor alerts in database"""
    
    print("🔍 CHECKING MONITOR ALERTS IN DATABASE")
    print("=" * 50)
    
    try:
        # Connect to database
        await connect_to_mongo()
        print("✅ Database connected")
        
        # Step 1: Check active monitors
        print(f"\n📊 STEP 1: Checking active monitors")
        
        all_monitors = await Monitor.find_all().to_list()
        active_monitors = await Monitor.find(Monitor.enabled == True).to_list()
        
        print(f"   📊 Total monitors: {len(all_monitors)}")
        print(f"   ✅ Active monitors: {len(active_monitors)}")
        
        if active_monitors:
            print(f"   📋 Active monitor details:")
            for i, monitor in enumerate(active_monitors, 1):
                print(f"      {i}. {monitor.name}")
                print(f"         🆔 ID: {monitor.id}")
                print(f"         👤 User: {monitor.userId}")
                print(f"         🪙 Symbols: {', '.join(monitor.symbols)}")
                print(f"         ⚠️ Threshold: {monitor.crash_threshold}%")
                print(f"         📢 Channels: {', '.join(monitor.notification_channels)}")
                print(f"         📅 Created: {monitor.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"         🔄 Last check: {monitor.last_check.strftime('%Y-%m-%d %H:%M:%S') if monitor.last_check else 'Never'}")
        else:
            print(f"   ⚠️ No active monitors found")
        
        # Step 2: Check all alerts
        print(f"\n🚨 STEP 2: Checking stored alerts")
        
        all_alerts = await MonitorAlert.find_all().to_list()
        recent_alerts = await MonitorAlert.find(
            MonitorAlert.createdAt >= datetime.utcnow() - timedelta(days=7)
        ).sort(-MonitorAlert.createdAt).to_list()
        
        print(f"   📊 Total alerts: {len(all_alerts)}")
        print(f"   📅 Recent alerts (7 days): {len(recent_alerts)}")
        
        if all_alerts:
            print(f"   📋 Alert summary:")
            
            # Group by symbol
            symbol_counts = {}
            for alert in all_alerts:
                symbol = alert.symbol
                if symbol not in symbol_counts:
                    symbol_counts[symbol] = 0
                symbol_counts[symbol] += 1
            
            for symbol, count in symbol_counts.items():
                print(f"      🪙 {symbol}: {count} alerts")
            
            # Show recent alerts
            if recent_alerts:
                print(f"\n   📅 Recent alerts:")
                for i, alert in enumerate(recent_alerts[:5], 1):  # Show last 5
                    print(f"      {i}. {alert.symbol} - {alert.price_drop:.2f}% drop")
                    print(f"         💰 Price: ${alert.current_price:,.2f}")
                    print(f"         📅 Time: {alert.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"         📢 Sent: {', '.join(alert.notification_channels) if alert.notification_channels else 'None'}")
                    print(f"         🎯 Confidence: {alert.confidence_level or 'Unknown'}")
                    print(f"         🤖 ASI: {'Yes' if alert.asi_analysis else 'No'}")
        else:
            print(f"   ⚠️ No alerts found in database")
            print(f"   💡 This could mean:")
            print(f"      - Monitor service hasn't detected any crashes yet")
            print(f"      - No active monitors are configured")
            print(f"      - Monitor service is not running")
            print(f"      - Crash thresholds are too high")
        
        # Step 3: Check users with monitors
        print(f"\n👤 STEP 3: Checking users with monitors")
        
        all_users = await User.find_all().to_list()
        users_with_monitors = [user for user in all_users if user.monitors]
        
        print(f"   👥 Total users: {len(all_users)}")
        print(f"   📊 Users with monitors: {len(users_with_monitors)}")
        
        if users_with_monitors:
            print(f"   📋 Users with monitors:")
            for i, user in enumerate(users_with_monitors, 1):
                print(f"      {i}. {user.firstName or user.username or 'Unknown'}")
                print(f"         📧 Email: {user.email or 'Not set'}")
                print(f"         📱 Telegram: {user.telegramId or 'Not set'}")
                print(f"         📊 Monitors: {len(user.monitors)}")
                print(f"         🔔 Email alerts: {'✅' if user.notificationPreferences.get('email_alerts') else '❌'}")
                print(f"         📱 Telegram alerts: {'✅' if user.notificationPreferences.get('telegram_alerts') else '❌'}")
        
        # Step 4: Check for monitoring issues
        print(f"\n🔍 STEP 4: Diagnosing potential issues")
        
        issues = []
        
        if len(active_monitors) == 0:
            issues.append("No active monitors configured")
        
        if len(all_alerts) == 0:
            issues.append("No alerts have been generated")
        
        if len(users_with_monitors) == 0:
            issues.append("No users have monitors configured")
        
        # Check if monitors have been checked recently
        stale_monitors = []
        for monitor in active_monitors:
            if not monitor.last_check or (datetime.utcnow() - monitor.last_check).total_seconds() > 3600:  # 1 hour
                stale_monitors.append(monitor)
        
        if stale_monitors:
            issues.append(f"{len(stale_monitors)} monitors haven't been checked recently")
        
        if issues:
            print(f"   ⚠️ Potential issues found:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"   ✅ No obvious issues detected")
        
        # Step 5: Recommendations
        print(f"\n💡 STEP 5: Recommendations")
        
        if len(active_monitors) == 0:
            print(f"   📊 Create monitors using the API:")
            print(f"      POST /monitors/ with user_id and monitor configuration")
        
        if len(all_alerts) == 0 and len(active_monitors) > 0:
            print(f"   🚨 To generate test alerts:")
            print(f"      - Lower crash thresholds (try 1-2%)")
            print(f"      - Check if monitor service is running")
            print(f"      - Verify price data is being fetched")
        
        if len(users_with_monitors) == 0:
            print(f"   👤 Create users and associate monitors:")
            print(f"      POST /users/ to create users")
            print(f"      POST /monitors/ to create monitors for users")
        
        print(f"\n🔄 To force alert generation for testing:")
        print(f"   python test/force_asi_test.py")
        
        return len(all_alerts) > 0
        
    except Exception as e:
        print(f"❌ Error checking alerts: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return False

async def main():
    """Main function"""
    
    print("🧪 MONITOR ALERTS DATABASE CHECK")
    print("=" * 60)
    
    has_alerts = await check_monitor_alerts()
    
    print("\n" + "=" * 60)
    if has_alerts:
        print("✅ ALERTS FOUND IN DATABASE")
        print("💡 The monitoring system is working and storing alerts!")
    else:
        print("❌ NO ALERTS FOUND IN DATABASE")
        print("💡 Check the recommendations above to start generating alerts")
    
    return has_alerts

if __name__ == "__main__":
    asyncio.run(main())
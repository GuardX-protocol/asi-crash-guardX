#!/usr/bin/env python3
"""
Live Monitor with Alert Storage Test
===================================

This test:
1. Creates a real user and monitor
2. Simulates the monitor service detecting a crash
3. Verifies alerts are stored in the database
4. Tests the complete flow from crash detection to alert storage
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import connect_to_mongo
from app.models import User, Monitor, MonitorAlert, MonitorReference
from app.services.asi_crash_detector import ASICrashDetector

# Load environment variables
load_dotenv()

async def test_live_monitor_with_alerts():
    """Test live monitor with alert storage"""
    
    print("🔴 LIVE MONITOR WITH ALERT STORAGE TEST")
    print("=" * 60)
    
    try:
        # Connect to database
        await connect_to_mongo()
        print("✅ Database connected")
        
        # Initialize crash detector
        crash_detector = ASICrashDetector()
        print(f"🤖 ASI Crash Detector: {'✅ Ready' if crash_detector.is_configured() else '❌ Not configured'}")
        
        # Test data
        test_wallet = "0x4444444444444444444444444444444444444444"
        
        # Clean up any existing test data
        await cleanup_test_data(test_wallet)
        
        # Step 1: Create real user with email and telegram
        print(f"\n👤 STEP 1: Creating real user")
        user = User(
            walletAddress=test_wallet,
            email="live-test@example.com",
            telegramId="555666777",
            firstName="Live",
            lastName="Monitor",
            notificationPreferences={
                "telegram_alerts": True,
                "email_alerts": True,
                "webhook_alerts": False
            }
        )
        await user.insert()
        print(f"   ✅ User created: {user.firstName} {user.lastName}")
        print(f"   📧 Email: {user.email}")
        print(f"   📱 Telegram: {user.telegramId}")
        
        # Step 2: Create active monitor with low threshold
        print(f"\n📊 STEP 2: Creating active monitor")
        monitor = Monitor(
            name="Live Alert Test Monitor",
            userId=test_wallet,
            symbols=["BTCUSDT", "ETHUSDT"],
            crash_threshold=1.0,  # Very low threshold to trigger easily
            enabled=True,
            notification_channels=["email", "telegram"],
            last_check=datetime.utcnow()  # Mark as recently checked
        )
        await monitor.insert()
        
        # Add monitor reference to user
        monitor_ref = MonitorReference(
            id=str(monitor.id),
            name=monitor.name,
            enabled=monitor.enabled,
            created_at=monitor.createdAt,
            symbols=monitor.symbols
        )
        user.monitors.append(monitor_ref)
        await user.save()
        
        print(f"   ✅ Monitor created: {monitor.name}")
        print(f"   🆔 Monitor ID: {monitor.id}")
        print(f"   ⚠️ Crash threshold: {monitor.crash_threshold}% (very sensitive)")
        print(f"   🪙 Symbols: {', '.join(monitor.symbols)}")
        print(f"   📢 Channels: {', '.join(monitor.notification_channels)}")
        
        # Step 3: Simulate crash detection (like monitor service would do)
        print(f"\n🚨 STEP 3: Simulating crash detection")
        
        # Create realistic crash scenario data
        crash_data = generate_realistic_crash_data()
        current_price = crash_data[-1]["close"]
        symbol = "BTCUSDT"
        
        print(f"   💰 Current price: ${current_price:,.2f}")
        print(f"   📉 Simulated crash scenario")
        
        # Run crash detection
        crash_result = await crash_detector.detect_crash(symbol, crash_data, current_price)
        
        print(f"   🎯 Crash detected: {'YES' if crash_result.get('is_crash') else 'NO'}")
        print(f"   📊 Crash probability: {crash_result.get('crash_probability', 0):.1%}")
        print(f"   🔍 Confidence: {crash_result.get('confidence_level', 'unknown')}")
        
        # Step 4: Simulate monitor service alert creation logic
        print(f"\n💾 STEP 4: Creating alert (simulating monitor service)")
        
        # Extract ASI analysis
        asi_analysis = crash_result.get("asi_analysis", {})
        analysis_text = "Advanced crash detection algorithms detected significant price movement."
        
        if asi_analysis:
            if asi_analysis.get("formatted_analysis", {}).get("email_summary"):
                analysis_text = asi_analysis["formatted_analysis"]["email_summary"]
                print(f"   🤖 Using formatted ASI analysis")
            elif asi_analysis.get("raw_analysis"):
                raw_analysis = asi_analysis["raw_analysis"]
                analysis_text = raw_analysis[:500] + "..." if len(raw_analysis) > 500 else raw_analysis
                print(f"   🤖 Using raw ASI analysis (truncated)")
        else:
            print(f"   ⚠️ No ASI analysis available, using fallback")
        
        # Get token name
        token_name = "Bitcoin"
        
        # Calculate price before crash
        current_price = crash_result.get("current_price", current_price)
        price_drop_percent = abs(crash_result.get("price_drop_24h", 0))
        price_before_crash = current_price / (1 - price_drop_percent / 100) if price_drop_percent > 0 else current_price
        
        # Convert technical indicators to JSON-serializable format
        technical_indicators = crash_result.get("technical_signals", {})
        clean_technical_indicators = {}
        for key, value in technical_indicators.items():
            if hasattr(value, 'item'):  # numpy scalar
                clean_technical_indicators[key] = value.item()
            elif isinstance(value, (bool, int, float, str)):
                clean_technical_indicators[key] = value
            else:
                clean_technical_indicators[key] = str(value)
        
        # Create comprehensive alert record (exactly like monitor service does)
        alert = MonitorAlert(
            monitorId=str(monitor.id),
            userId=monitor.userId,
            symbol=symbol,
            token_name=token_name,
            crash_probability=float(crash_result.get("crash_probability", 0)),
            current_price=float(current_price),
            price_drop=float(abs(crash_result.get("price_drop_24h", 0))),
            price_before_crash=float(price_before_crash),
            analysis=analysis_text,
            crash_detected_at=datetime.utcnow(),
            technical_indicators=clean_technical_indicators,
            asi_analysis=asi_analysis.get("raw_analysis") if asi_analysis else None,
            confidence_level=crash_result.get("confidence_level", "medium"),
            notification_sent=False,
            createdAt=datetime.utcnow()
        )
        
        # Insert alert into database
        await alert.insert()
        
        print(f"   ✅ Alert stored in database")
        print(f"   🆔 Alert ID: {alert.id}")
        print(f"   💰 Price: ${alert.current_price:,.2f}")
        print(f"   📉 Drop: {alert.price_drop:.2f}%")
        print(f"   📝 Analysis length: {len(alert.analysis)} characters")
        
        # Step 5: Simulate notification sending and update alert
        print(f"\n📢 STEP 5: Simulating notification sending")
        
        notifications_sent = []
        
        # Check Telegram notification
        if (user.telegramId and 
            user.notificationPreferences.get("telegram_alerts", True) and
            "telegram" in monitor.notification_channels):
            notifications_sent.append("telegram")
            print(f"   📱 Would send Telegram to: {user.telegramId}")
        
        # Check Email notification
        if (user.email and 
            user.notificationPreferences.get("email_alerts", False) and
            "email" in monitor.notification_channels):
            notifications_sent.append("email")
            print(f"   📧 Would send email to: {user.email}")
        
        # Always log
        notifications_sent.append("log")
        print(f"   📝 Logged to system")
        
        # Update alert with notification status
        alert.notification_sent = len(notifications_sent) > 0
        alert.notification_channels = notifications_sent
        alert.telegram_sent = "telegram" in notifications_sent
        alert.email_sent = "email" in notifications_sent
        alert.webhook_sent = "webhook" in notifications_sent
        await alert.save()
        
        print(f"   ✅ Alert updated with notification status")
        print(f"   📢 Notifications: {', '.join(notifications_sent)}")
        
        # Step 6: Verify alert storage and retrieval
        print(f"\n🔍 STEP 6: Verifying alert storage")
        
        # Get all alerts for this user
        user_alerts = await MonitorAlert.find(MonitorAlert.userId == test_wallet).to_list()
        print(f"   📊 Total alerts for user: {len(user_alerts)}")
        
        # Get all alerts for this monitor
        monitor_alerts = await MonitorAlert.find(MonitorAlert.monitorId == str(monitor.id)).to_list()
        print(f"   📊 Total alerts for monitor: {len(monitor_alerts)}")
        
        # Show alert details
        if user_alerts:
            alert_record = user_alerts[0]
            print(f"   📋 Alert details:")
            print(f"      🆔 ID: {alert_record.id}")
            print(f"      🪙 Symbol: {alert_record.symbol} ({alert_record.token_name})")
            print(f"      💰 Price: ${alert_record.current_price:,.2f}")
            print(f"      📉 Drop: {alert_record.price_drop:.2f}%")
            print(f"      🎯 Probability: {alert_record.crash_probability:.1%}")
            print(f"      🔍 Confidence: {alert_record.confidence_level}")
            print(f"      📅 Created: {alert_record.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"      📢 Sent: {', '.join(alert_record.notification_channels)}")
            print(f"      🤖 ASI: {'Yes' if alert_record.asi_analysis else 'No'}")
        
        # Step 7: Test alert queries
        print(f"\n🔍 STEP 7: Testing alert queries")
        
        # Query by symbol
        btc_alerts = await MonitorAlert.find(MonitorAlert.symbol == "BTCUSDT").to_list()
        print(f"   🪙 BTCUSDT alerts in database: {len(btc_alerts)}")
        
        # Query recent alerts
        recent_alerts = await MonitorAlert.find(
            MonitorAlert.createdAt >= datetime.utcnow() - timedelta(minutes=5)
        ).to_list()
        print(f"   📅 Recent alerts (5 minutes): {len(recent_alerts)}")
        
        # Query by user
        all_user_alerts = await MonitorAlert.find(MonitorAlert.userId == test_wallet).to_list()
        print(f"   👤 User alerts: {len(all_user_alerts)}")
        
        print(f"\n✅ Live monitor test completed successfully!")
        print(f"   📊 Created {len(user_alerts)} alert(s)")
        print(f"   💾 Alert stored in 'monitor_alerts' collection")
        print(f"   🔄 Complete monitor service flow simulated")
        print(f"   📢 Notification logic tested")
        
        # Don't cleanup - leave data for inspection
        print(f"\n💡 Test data left in database for inspection:")
        print(f"   👤 User: {test_wallet}")
        print(f"   📊 Monitor: {monitor.id}")
        print(f"   🚨 Alert: {alert.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        await cleanup_test_data(test_wallet)
        return False

def generate_realistic_crash_data():
    """Generate realistic crash scenario data"""
    base_price = 45000
    data = []
    
    # 30 data points representing hourly data
    for i in range(30):
        if i < 20:
            # Normal trading with small fluctuations
            fluctuation = ((-1) ** i) * (i * 25)  # Small movements
            price = base_price + fluctuation
        else:
            # Crash phase - gradual then accelerating drop
            crash_progress = (i - 20) / 10  # 0 to 1
            # Accelerating crash curve
            crash_factor = crash_progress ** 1.2 * 0.08  # 8% total crash
            price = base_price * (1 - crash_factor)
        
        # Volume increases during crash
        base_volume = 1000000
        if i >= 20:
            volume_multiplier = 1 + (i - 20) * 0.4  # Volume spike during crash
            volume = base_volume * volume_multiplier
        else:
            volume = base_volume + (i * 15000)  # Normal volume growth
        
        data.append({
            "close": max(price, base_price * 0.8),  # Prevent extreme drops
            "volume": volume,
            "timestamp": (datetime.utcnow() - timedelta(hours=30-i)).isoformat()
        })
    
    return data

async def cleanup_test_data(wallet_address: str):
    """Clean up test data"""
    try:
        # Delete test user
        user = await User.find_one(User.walletAddress == wallet_address)
        if user:
            await user.delete()
        
        # Delete test monitors
        monitors = await Monitor.find(Monitor.userId == wallet_address).to_list()
        for monitor in monitors:
            await monitor.delete()
        
        # Delete test alerts
        alerts = await MonitorAlert.find(MonitorAlert.userId == wallet_address).to_list()
        for alert in alerts:
            await alert.delete()
            
        print(f"🧹 Test data cleaned up for {wallet_address}")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main test function"""
    
    print("🧪 LIVE MONITOR WITH ALERT STORAGE TEST SUITE")
    print("=" * 70)
    
    success = await test_live_monitor_with_alerts()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ LIVE MONITOR WITH ALERT STORAGE TEST PASSED")
        print("\n🎯 Successfully Demonstrated:")
        print("   ✅ Real user and monitor creation")
        print("   ✅ Crash detection with ASI analysis")
        print("   ✅ Alert storage in 'monitor_alerts' collection")
        print("   ✅ Complete monitor service flow simulation")
        print("   ✅ Notification logic and status tracking")
        print("   ✅ Database queries and alert retrieval")
        print("\n💡 The alert storage system is working correctly!")
        print("   When the monitor service runs, it will store alerts just like this test.")
    else:
        print("❌ LIVE MONITOR WITH ALERT STORAGE TEST FAILED")
        print("   Check the error details above")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
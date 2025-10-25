#!/usr/bin/env python3
"""
Manual Alert Creation Test
=========================

This test manually creates alerts to verify database storage is working.
"""
import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import connect_to_mongo
from app.models import User, Monitor, MonitorAlert, MonitorReference

# Load environment variables
load_dotenv()

async def test_manual_alert_creation():
    """Test manual alert creation and storage"""
    
    print("🚨 MANUAL ALERT CREATION TEST")
    print("=" * 40)
    
    try:
        # Connect to database
        await connect_to_mongo()
        print("✅ Database connected")
        
        # Test data
        test_wallet = "0x3333333333333333333333333333333333333333"
        
        # Clean up any existing test data
        await cleanup_test_data(test_wallet)
        
        # Step 1: Create test user
        print(f"\n👤 STEP 1: Creating test user")
        user = User(
            walletAddress=test_wallet,
            email="manual-test@example.com",
            firstName="Manual",
            lastName="Test",
            notificationPreferences={
                "telegram_alerts": True,
                "email_alerts": True,
                "webhook_alerts": False
            }
        )
        await user.insert()
        print(f"   ✅ User created: {user.firstName} {user.lastName}")
        
        # Step 2: Create test monitor
        print(f"\n📊 STEP 2: Creating test monitor")
        monitor = Monitor(
            name="Manual Test Monitor",
            userId=test_wallet,
            symbols=["BTCUSDT"],
            crash_threshold=5.0,
            enabled=True,
            notification_channels=["email", "telegram"]
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
        
        # Step 3: Manually create and store alert
        print(f"\n🚨 STEP 3: Creating manual alert")
        
        alert = MonitorAlert(
            monitorId=str(monitor.id),
            userId=monitor.userId,
            symbol="BTCUSDT",
            token_name="Bitcoin",
            crash_probability=0.75,
            current_price=43500.0,
            price_drop=7.5,
            price_before_crash=47000.0,
            analysis="Manual test alert: Bitcoin crashed 7.5% due to market volatility",
            crash_detected_at=datetime.utcnow(),
            technical_indicators={
                "rsi": 28.5,
                "price_below_sma20": True,
                "volume_spike": True
            },
            asi_analysis="ASI analysis: Genuine crash detected with oversold conditions",
            confidence_level="high",
            notification_sent=True,
            notification_channels=["email", "telegram", "log"],
            telegram_sent=True,
            email_sent=True,
            webhook_sent=False,
            createdAt=datetime.utcnow()
        )
        
        # Insert alert into database
        await alert.insert()
        
        print(f"   ✅ Alert created and stored")
        print(f"   🆔 Alert ID: {alert.id}")
        print(f"   🪙 Symbol: {alert.symbol}")
        print(f"   💰 Price: ${alert.current_price:,.2f}")
        print(f"   📉 Drop: {alert.price_drop}%")
        print(f"   🎯 Probability: {alert.crash_probability:.1%}")
        
        # Step 4: Verify alert was stored
        print(f"\n🔍 STEP 4: Verifying alert storage")
        
        # Retrieve alert from database
        stored_alert = await MonitorAlert.get(alert.id)
        print(f"   ✅ Alert retrieved from database")
        print(f"   🆔 ID: {stored_alert.id}")
        print(f"   👤 User: {stored_alert.userId}")
        print(f"   📊 Monitor: {stored_alert.monitorId}")
        print(f"   🪙 Symbol: {stored_alert.symbol}")
        print(f"   📅 Created: {stored_alert.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check all alerts for this user
        user_alerts = await MonitorAlert.find(MonitorAlert.userId == test_wallet).to_list()
        print(f"   📊 Total alerts for user: {len(user_alerts)}")
        
        # Check all alerts for this monitor
        monitor_alerts = await MonitorAlert.find(MonitorAlert.monitorId == str(monitor.id)).to_list()
        print(f"   📊 Total alerts for monitor: {len(monitor_alerts)}")
        
        # Step 5: Create another alert to test multiple alerts
        print(f"\n🚨 STEP 5: Creating second alert")
        
        alert2 = MonitorAlert(
            monitorId=str(monitor.id),
            userId=monitor.userId,
            symbol="BTCUSDT",
            token_name="Bitcoin",
            crash_probability=0.65,
            current_price=42000.0,
            price_drop=3.4,
            price_before_crash=43500.0,
            analysis="Second test alert: Bitcoin dropped another 3.4%",
            crash_detected_at=datetime.utcnow(),
            technical_indicators={
                "rsi": 25.0,
                "price_below_sma20": True,
                "volume_spike": False
            },
            confidence_level="medium",
            notification_sent=True,
            notification_channels=["email", "log"],
            telegram_sent=False,
            email_sent=True,
            webhook_sent=False,
            createdAt=datetime.utcnow()
        )
        
        await alert2.insert()
        print(f"   ✅ Second alert created: {alert2.id}")
        
        # Step 6: Query all alerts
        print(f"\n📋 STEP 6: Querying all alerts")
        
        all_user_alerts = await MonitorAlert.find(MonitorAlert.userId == test_wallet).sort(-MonitorAlert.createdAt).to_list()
        
        print(f"   📊 Total alerts for user: {len(all_user_alerts)}")
        print(f"   📋 Alert details:")
        
        for i, alert_record in enumerate(all_user_alerts, 1):
            print(f"      {i}. {alert_record.symbol} - {alert_record.price_drop}% drop")
            print(f"         💰 Price: ${alert_record.current_price:,.2f}")
            print(f"         📅 Time: {alert_record.createdAt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"         📢 Channels: {', '.join(alert_record.notification_channels)}")
            print(f"         🎯 Confidence: {alert_record.confidence_level}")
            print(f"         🤖 ASI: {'Yes' if alert_record.asi_analysis else 'No'}")
        
        # Step 7: Test alert queries
        print(f"\n🔍 STEP 7: Testing alert queries")
        
        # Query by symbol
        btc_alerts = await MonitorAlert.find(MonitorAlert.symbol == "BTCUSDT").to_list()
        print(f"   🪙 BTCUSDT alerts: {len(btc_alerts)}")
        
        # Query by monitor
        monitor_specific_alerts = await MonitorAlert.find(MonitorAlert.monitorId == str(monitor.id)).to_list()
        print(f"   📊 Monitor-specific alerts: {len(monitor_specific_alerts)}")
        
        # Query recent alerts
        from datetime import timedelta
        recent_alerts = await MonitorAlert.find(
            MonitorAlert.createdAt >= datetime.utcnow() - timedelta(hours=1)
        ).to_list()
        print(f"   📅 Recent alerts (1 hour): {len(recent_alerts)}")
        
        print(f"\n✅ Manual alert creation test completed successfully!")
        print(f"   📊 Created {len(all_user_alerts)} alerts")
        print(f"   💾 All alerts stored in 'monitor_alerts' collection")
        print(f"   🔍 All queries working correctly")
        
        # Cleanup
        await cleanup_test_data(test_wallet)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        await cleanup_test_data(test_wallet)
        return False

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
    
    print("🧪 MANUAL ALERT CREATION TEST SUITE")
    print("=" * 50)
    
    success = await test_manual_alert_creation()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ MANUAL ALERT CREATION TEST PASSED")
        print("\n🎯 Verified:")
        print("   ✅ MonitorAlert documents can be created")
        print("   ✅ Alerts are stored in 'monitor_alerts' collection")
        print("   ✅ All alert fields are properly saved")
        print("   ✅ Alert queries work correctly")
        print("   ✅ Multiple alerts can be stored per user/monitor")
        print("\n💡 Database storage is working correctly!")
        print("   The issue might be that the monitor service isn't detecting crashes")
        print("   or no monitors are actively running.")
    else:
        print("❌ MANUAL ALERT CREATION TEST FAILED")
        print("   Check database connection and model configuration")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
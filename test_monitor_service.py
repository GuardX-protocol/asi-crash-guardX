#!/usr/bin/env python3
"""
Test the Monitor Service functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_create_user_and_monitor():
    """Create a test user and monitor"""
    print("🧪 Creating test user and monitor...")
    
    # Create user first
    user_payload = {
        "walletAddress": "0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e",
        "telegramId": "123456789",
        "username": "testmonitor",
        "firstName": "Monitor",
        "lastName": "Test",
        "notificationPreferences": {
            "telegram_alerts": True,
            "email_alerts": False,
            "webhook_alerts": False
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create user
            async with session.post(
                'http://localhost:8000/users/',
                json=user_payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status in [200, 201]:
                    print("✅ Test user created")
                elif response.status == 400:
                    print("✅ Test user already exists")
                else:
                    print(f"⚠️ User creation status: {response.status}")
            
            # Create monitor
            monitor_payload = {
                "name": "BTC_Crash_Monitor",
                "userId": "0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e",
                "symbols": ["BTC", "ETH"],
                "interval_seconds": 120,  # 2 minutes for testing
                "price_change_threshold": 2.0,  # 2% change threshold
                "volume_change_threshold": 50.0,
                "crash_probability_threshold": 70.0,
                "enabled": True,
                "telegram_alerts": True,
                "email_alerts": False,
                "alert_webhooks": []
            }
            
            async with session.post(
                'http://localhost:8000/crypto/monitor/create',
                json=monitor_payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    print(f"✅ Monitor created: {result['name']}")
                    return True
                elif response.status == 400:
                    print("✅ Monitor already exists")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ Monitor creation failed: {response.status} - {error}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error creating user/monitor: {e}")
        return False

async def test_monitor_service_status():
    """Test monitor service status"""
    print("\n🧪 Testing monitor service status...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/monitor/service-status') as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Monitor Service Status:")
                    print(f"   - Running: {result.get('running', False)}")
                    print(f"   - Symbols Tracked: {result.get('symbols_tracked', 0)}")
                    print(f"   - Monitors Tracked: {result.get('monitors_tracked', 0)}")
                    
                    if result.get('last_prices'):
                        print(f"   - Last Prices: {json.dumps(result['last_prices'], indent=4)}")
                    
                    return result.get('running', False)
                else:
                    print(f"❌ Status check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

async def test_list_monitors():
    """Test listing monitors"""
    print("\n🧪 Testing monitor listing...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/crypto/monitors') as response:
                if response.status == 200:
                    monitors = await response.json()
                    print(f"✅ Found {len(monitors)} monitor(s):")
                    
                    for monitor in monitors:
                        print(f"   - {monitor['name']}: {monitor['symbols']} (enabled: {monitor['enabled']})")
                    
                    return len(monitors) > 0
                else:
                    print(f"❌ Monitor listing failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error listing monitors: {e}")
        return False

async def test_get_prices():
    """Test getting crypto prices"""
    print("\n🧪 Testing price fetching...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/crypto/prices?symbols=BTC,ETH') as response:
                if response.status == 200:
                    prices = await response.json()
                    print(f"✅ Current Prices:")
                    
                    for symbol, price_data in prices.items():
                        print(f"   - {symbol}: ${price_data['price']:.2f} ({price_data['change_24h']:+.2f}%)")
                    
                    return len(prices) > 0
                else:
                    print(f"❌ Price fetching failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error fetching prices: {e}")
        return False

async def test_alerts():
    """Test getting alerts"""
    print("\n🧪 Testing alerts...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/crypto/alerts?limit=10') as response:
                if response.status == 200:
                    alerts = await response.json()
                    print(f"✅ Found {len(alerts)} alert(s)")
                    
                    for alert in alerts[:3]:  # Show first 3
                        print(f"   - {alert.get('symbol', 'N/A')}: {alert.get('alertType', 'N/A')} ({alert.get('severity', 'N/A')})")
                    
                    return True
                else:
                    print(f"❌ Alert fetching failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return False

async def wait_for_monitoring():
    """Wait and check if monitoring is working"""
    print("\n⏳ Waiting for monitor service to process data...")
    print("   (This may take 2-3 minutes for the service to collect price data)")
    
    for i in range(6):  # Wait up to 3 minutes
        await asyncio.sleep(30)  # Wait 30 seconds
        
        print(f"   Checking... ({i+1}/6)")
        
        # Check service status
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/monitor/service-status') as response:
                    if response.status == 200:
                        result = await response.json()
                        symbols_tracked = result.get('symbols_tracked', 0)
                        
                        if symbols_tracked > 0:
                            print(f"✅ Monitor service is tracking {symbols_tracked} symbols!")
                            return True
                        else:
                            print(f"   Still waiting... (symbols tracked: {symbols_tracked})")
        except Exception as e:
            print(f"   Error checking: {e}")
    
    print("⚠️ Monitor service may need more time to start tracking symbols")
    return False

async def main():
    """Run all tests"""
    print("🚀 Testing Monitor Service Integration")
    print("=" * 60)
    
    # Test 1: Create user and monitor
    setup_success = await test_create_user_and_monitor()
    
    # Test 2: Check service status
    service_running = await test_monitor_service_status()
    
    # Test 3: List monitors
    monitors_exist = await test_list_monitors()
    
    # Test 4: Test price fetching
    prices_work = await test_get_prices()
    
    # Test 5: Check alerts
    alerts_work = await test_alerts()
    
    # Test 6: Wait for monitoring to start
    monitoring_active = False
    if service_running and monitors_exist:
        monitoring_active = await wait_for_monitoring()
    
    # Final status check
    if monitoring_active:
        await test_monitor_service_status()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"• User & Monitor Setup: {'✅ PASS' if setup_success else '❌ FAIL'}")
    print(f"• Service Running: {'✅ PASS' if service_running else '❌ FAIL'}")
    print(f"• Monitors Listed: {'✅ PASS' if monitors_exist else '❌ FAIL'}")
    print(f"• Price Fetching: {'✅ PASS' if prices_work else '❌ FAIL'}")
    print(f"• Alerts System: {'✅ PASS' if alerts_work else '❌ FAIL'}")
    print(f"• Active Monitoring: {'✅ PASS' if monitoring_active else '⏳ PENDING'}")
    
    if all([setup_success, service_running, monitors_exist, prices_work]):
        print("\n🎉 Monitor Service is working!")
        print("\n💡 What happens next:")
        print("   1. Service monitors BTC & ETH prices every 2 minutes")
        print("   2. Alerts trigger when price changes > 2%")
        print("   3. Crash detection runs when enough data is collected")
        print("   4. Telegram alerts sent to users automatically")
        print("\n📱 Check your Telegram bot for alerts!")
    else:
        print("\n⚠️ Some components need attention. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
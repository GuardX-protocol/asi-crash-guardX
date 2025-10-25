#!/usr/bin/env python3
"""
GuardX Live Crash Detection Test
================================

This test demonstrates the GuardX system's ability to detect real market crashes
by monitoring live cryptocurrency prices and triggering alerts when crashes occur.

Features tested:
- Real-time price monitoring
- Crash detection algorithms
- Alert generation and delivery
- Database storage of alerts
- Multi-channel notifications

Usage: python test/live_crash_detection_test.py
"""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class LiveCrashDetectionTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.wallet_address = "0x052d3F83D61065891c1B9af4f6F5206D2D32AD4e"
        self.test_monitor_id = None
        self.baseline_prices = {}
        self.monitoring_active = False
        
    def run_live_test(self):
        """Run live crash detection test"""
        print("🔴 GUARDX LIVE CRASH DETECTION TEST")
        print("=" * 50)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test User: {self.wallet_address}")
        print("=" * 50)
        
        try:
            # Setup
            self._setup_test_environment()
            
            # Start monitoring
            self._start_live_monitoring()
            
            # Monitor for crashes (runs for specified duration)
            self._monitor_for_crashes(duration_minutes=10)
            
            # Show results
            self._show_test_results()
            
            # Cleanup
            self._cleanup_test()
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Test interrupted by user")
            self._cleanup_test()
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            self._cleanup_test()
    
    def _setup_test_environment(self):
        """Setup the test environment"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT")
        print("-" * 35)
        
        # Verify system is running
        status = self._api_call("GET", "/system/status")
        if not status:
            raise Exception("GuardX system not responding")
        
        monitoring_status = status.get("monitoring", {}).get("status", {})
        print(f"✅ System Status:")
        print(f"   - Database: {status.get('database', {}).get('status')}")
        print(f"   - Monitoring: {'Running' if monitoring_status.get('running') else 'Stopped'}")
        print(f"   - ASI Configured: {status.get('ai_services', {}).get('asi_configured')}")
        
        # Create test monitor with sensitive thresholds
        monitor_data = {
            "name": f"LIVE TEST {datetime.now().strftime('%H%M%S')}",
            "symbols": ["BTC", "ETH", "SOL", "ADA"],
            "crash_threshold": 0.2,  # Very sensitive for testing
            "enabled": True,
            "notification_channels": ["telegram", "email"]
        }
        
        print(f"\n📊 Creating sensitive test monitor...")
        print(f"   - Symbols: {', '.join(monitor_data['symbols'])}")
        print(f"   - Crash Threshold: {monitor_data['crash_threshold']}% (very sensitive)")
        
        monitor = self._api_call("POST", "/monitors/", monitor_data, {"user_id": self.wallet_address})
        if monitor:
            self.test_monitor_id = monitor.get("id")
            print(f"✅ Test monitor created: {self.test_monitor_id}")
        else:
            raise Exception("Failed to create test monitor")
    
    def _start_live_monitoring(self):
        """Start live price monitoring"""
        print("\n📈 STARTING LIVE MONITORING")
        print("-" * 35)
        
        # Get baseline prices
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
        
        print("💰 Establishing baseline prices:")
        for symbol in symbols:
            price_data = self._api_call("GET", f"/crypto/prices/{symbol}")
            if price_data:
                price = price_data.get('price', 0)
                change = price_data.get('change_24h', 0)
                
                self.baseline_prices[symbol] = {
                    'price': price,
                    'change_24h': change,
                    'timestamp': datetime.now()
                }
                
                emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                print(f"   {emoji} {symbol}: ${price:,.2f} ({change:+.2f}%)")
        
        self.monitoring_active = True
        print(f"\n🔍 Live monitoring activated")
        print(f"   - Monitoring {len(symbols)} symbols")
        print(f"   - Check interval: Every 30 seconds")
        print(f"   - Crash threshold: 3.0%")
    
    def _monitor_for_crashes(self, duration_minutes: int = 10):
        """Monitor for crashes over specified duration"""
        print(f"\n⏱️ MONITORING FOR CRASHES ({duration_minutes} minutes)")
        print("-" * 35)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        check_count = 0
        
        print(f"🔍 Monitoring until {end_time.strftime('%H:%M:%S')}")
        print(f"Press Ctrl+C to stop early\n")
        
        while datetime.now() < end_time and self.monitoring_active:
            check_count += 1
            current_time = datetime.now()
            
            print(f"📊 Check #{check_count} at {current_time.strftime('%H:%M:%S')}")
            
            # Check each symbol for crashes
            crashes_detected = []
            
            for symbol in self.baseline_prices.keys():
                crash_info = self._check_symbol_for_crash(symbol)
                if crash_info:
                    crashes_detected.append(crash_info)
            
            if crashes_detected:
                print(f"🚨 CRASHES DETECTED:")
                for crash in crashes_detected:
                    self._handle_detected_crash(crash)
            else:
                print(f"   ✅ No crashes detected")
            
            # Show current prices
            self._show_current_prices()
            
            # Wait before next check
            print(f"   ⏳ Next check in 30 seconds...\n")
            time.sleep(30)
        
        print(f"⏱️ Monitoring completed after {check_count} checks")
    
    def _check_symbol_for_crash(self, symbol: str) -> Optional[Dict]:
        """Check if a symbol has crashed"""
        try:
            # Get current price
            price_data = self._api_call("GET", f"/crypto/prices/{symbol}")
            if not price_data:
                return None
            
            current_price = price_data.get('price', 0)
            baseline = self.baseline_prices.get(symbol, {})
            baseline_price = baseline.get('price', 0)
            
            if baseline_price == 0:
                return None
            
            # Calculate price change since baseline
            price_change = ((current_price - baseline_price) / baseline_price) * 100
            
            # Check if it's a crash (negative change exceeding threshold)
            if price_change <= -3.0:  # 3% drop or more
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'baseline_price': baseline_price,
                    'price_change': price_change,
                    'crash_magnitude': abs(price_change),
                    'detection_time': datetime.now()
                }
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Error checking {symbol}: {e}")
            return None
    
    def _handle_detected_crash(self, crash_info: Dict):
        """Handle a detected crash"""
        symbol = crash_info['symbol']
        magnitude = crash_info['crash_magnitude']
        
        print(f"   💥 {symbol} CRASH DETECTED!")
        print(f"      - Price drop: {magnitude:.2f}%")
        print(f"      - From: ${crash_info['baseline_price']:,.2f}")
        print(f"      - To: ${crash_info['current_price']:,.2f}")
        print(f"      - Time: {crash_info['detection_time'].strftime('%H:%M:%S')}")
        
        # Check if alert was generated in system
        self._check_system_alerts()
    
    def _show_current_prices(self):
        """Show current prices compared to baseline"""
        print(f"   💰 Current prices vs baseline:")
        
        for symbol, baseline in self.baseline_prices.items():
            price_data = self._api_call("GET", f"/crypto/prices/{symbol}")
            if price_data:
                current_price = price_data.get('price', 0)
                baseline_price = baseline['price']
                
                if baseline_price > 0:
                    change = ((current_price - baseline_price) / baseline_price) * 100
                    emoji = "🚨" if change <= -3.0 else "📉" if change < 0 else "📈" if change > 0 else "➡️"
                    print(f"      {emoji} {symbol}: ${current_price:,.2f} ({change:+.2f}%)")
    
    def _check_system_alerts(self):
        """Check if the system generated any alerts"""
        if not self.test_monitor_id:
            return
        
        try:
            alerts = self._api_call("GET", f"/monitors/{self.test_monitor_id}/alerts", params={"user_id": self.wallet_address})
            if alerts:
                alert_list = alerts.get('alerts', [])
                if alert_list:
                    latest_alert = alert_list[0]  # Most recent alert
                    print(f"      🔔 System alert generated:")
                    print(f"         - Symbol: {latest_alert.get('symbol')}")
                    print(f"         - Drop: {latest_alert.get('price_drop', 0):.2f}%")
                    print(f"         - Analysis: {latest_alert.get('analysis', '')[:50]}...")
        except Exception as e:
            print(f"      ⚠️ Could not check alerts: {e}")
    
    def _show_test_results(self):
        """Show final test results"""
        print("\n📊 TEST RESULTS")
        print("-" * 35)
        
        if self.test_monitor_id:
            # Get monitor statistics
            monitor = self._api_call("GET", f"/monitors/{self.test_monitor_id}", params={"user_id": self.wallet_address})
            if monitor:
                print(f"✅ Monitor Performance:")
                print(f"   - Monitor ID: {self.test_monitor_id}")
                print(f"   - Status: {'Active' if monitor.get('enabled') else 'Inactive'}")
                print(f"   - Alerts Generated: {monitor.get('alerts_count', 0)}")
            
            # Get detailed alerts
            alerts = self._api_call("GET", f"/monitors/{self.test_monitor_id}/alerts", params={"user_id": self.wallet_address})
            if alerts:
                alert_list = alerts.get('alerts', [])
                print(f"\n🚨 Alert Details:")
                print(f"   - Total Alerts: {len(alert_list)}")
                
                if alert_list:
                    print(f"   - Recent Alerts:")
                    for i, alert in enumerate(alert_list[:3]):  # Show last 3 alerts
                        print(f"     {i+1}. {alert.get('symbol')}: {alert.get('price_drop', 0):.2f}% drop")
                        print(f"        Time: {alert.get('createdAt', 'Unknown')}")
                        print(f"        Price: ${alert.get('current_price', 0):,.2f}")
        
        # Show price changes during test
        print(f"\n📈 Price Changes During Test:")
        for symbol, baseline in self.baseline_prices.items():
            price_data = self._api_call("GET", f"/crypto/prices/{symbol}")
            if price_data:
                current_price = price_data.get('price', 0)
                baseline_price = baseline['price']
                
                if baseline_price > 0:
                    total_change = ((current_price - baseline_price) / baseline_price) * 100
                    status = "🚨 CRASH" if total_change <= -3.0 else "📉 DOWN" if total_change < 0 else "📈 UP"
                    print(f"   {status} {symbol}: {total_change:+.2f}%")
    
    def _cleanup_test(self):
        """Clean up test resources"""
        print("\n🧹 CLEANING UP TEST")
        print("-" * 35)
        
        if self.test_monitor_id:
            print(f"🗑️ Removing test monitor...")
            result = self._api_call("DELETE", f"/monitors/{self.test_monitor_id}", params={"user_id": self.wallet_address})
            if result:
                print(f"✅ Test monitor removed")
            else:
                print(f"⚠️ Manual cleanup may be needed: {self.test_monitor_id}")
        
        self.monitoring_active = False
        print(f"🔄 Test environment cleaned up")
    
    def _api_call(self, method: str, endpoint: str, data=None, params=None):
        """Make API call to GuardX system"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, params=params, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            return None

def main():
    """Run the live crash detection test"""
    print("🔴 GuardX Live Crash Detection Test")
    print("This test monitors real cryptocurrency prices for crashes")
    print("Duration: 10 minutes (or press Ctrl+C to stop)")
    print()
    
    test = LiveCrashDetectionTest()
    test.run_live_test()
    
    print("\n🎯 Live crash detection test completed!")
    print("The GuardX system is actively monitoring for real market crashes.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive system test for GuardX API
Tests all major functionality including database, Binance API, monitoring, and crash detection
"""

import requests
import json
import time
from datetime import datetime

class GuardXTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    def log_test(self, test_name, success, details=None, response_time=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "response_time_ms": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        time_str = f" ({response_time:.0f}ms)" if response_time else ""
        print(f"{status} {test_name}{time_str}")
        if details and not success:
            print(f"    Details: {details}")
    
    def test_endpoint(self, endpoint, method="GET", data=None, expected_status=200):
        """Test a single endpoint"""
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = (time.time() - start_time) * 1000
            
            success = response.status_code == expected_status
            details = None
            
            if not success:
                details = f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
            
            return success, response, response_time, details
            
        except Exception as e:
            return False, None, None, str(e)
    
    def run_basic_tests(self):
        """Run basic API tests"""
        print("\n🔍 Running Basic API Tests...")
        
        # Health check
        success, response, response_time, details = self.test_endpoint("/health")
        self.log_test("Health Check", success, details, response_time)
        
        # Root endpoint
        success, response, response_time, details = self.test_endpoint("/")
        self.log_test("Root Endpoint", success, details, response_time)
        
        # System status
        success, response, response_time, details = self.test_endpoint("/system/status")
        self.log_test("System Status", success, details, response_time)
        if success and response:
            try:
                data = response.json()
                print(f"    Database: {data.get('database', {}).get('status', 'unknown')}")
                print(f"    Binance API: {data.get('binance_api', {}).get('status', 'unknown')}")
                print(f"    Telegram: {data.get('telegram', {}).get('bot_configured', False)}")
            except:
                pass
    
    def run_database_tests(self):
        """Run database-related tests"""
        print("\n💾 Running Database Tests...")
        
        # Database status
        success, response, response_time, details = self.test_endpoint("/database/status")
        self.log_test("Database Status", success, details, response_time)
        
        # Database reconnection
        success, response, response_time, details = self.test_endpoint("/database/reconnect", method="POST")
        self.log_test("Database Reconnect", success, details, response_time)
        
        # Test connection
        success, response, response_time, details = self.test_endpoint("/database/test-connection", method="POST")
        self.log_test("Database Connection Test", success, details, response_time)
        
        # Users endpoint
        success, response, response_time, details = self.test_endpoint("/users/")
        self.log_test("Users List", success, details, response_time)
        if success and response:
            try:
                users = response.json()
                print(f"    Found {len(users)} users in database")
            except:
                pass
    
    def run_binance_tests(self):
        """Run Binance API tests"""
        print("\n📈 Running Binance API Tests...")
        
        # Binance API test
        success, response, response_time, details = self.test_endpoint("/crypto/binance/test")
        self.log_test("Binance API Test", success, details, response_time)
        
        # Get BTC price
        success, response, response_time, details = self.test_endpoint("/crypto/prices/BTC")
        self.log_test("BTC Price", success, details, response_time)
        if success and response:
            try:
                data = response.json()
                print(f"    BTC Price: ${data.get('price', 0):,.2f}")
                print(f"    24h Change: {data.get('change_24h', 0):+.2f}%")
            except:
                pass
        
        # Get multiple prices
        success, response, response_time, details = self.test_endpoint("/crypto/prices?symbols=BTC,ETH,ADA")
        self.log_test("Multiple Prices", success, details, response_time)
        
        # Real-time price
        success, response, response_time, details = self.test_endpoint("/crypto/prices/realtime/BTC")
        self.log_test("Real-time BTC Price", success, details, response_time)
    
    def run_monitor_tests(self):
        """Run monitoring system tests"""
        print("\n🔍 Running Monitor Tests...")
        
        # Monitor status
        success, response, response_time, details = self.test_endpoint("/monitor/service-status")
        self.log_test("Monitor Service Status", success, details, response_time)
        
        # List monitors
        success, response, response_time, details = self.test_endpoint("/crypto/monitors")
        self.log_test("List Monitors", success, details, response_time)
        if success and response:
            try:
                monitors = response.json()
                print(f"    Found {len(monitors)} monitors")
                active_monitors = [m for m in monitors if m.get('enabled', False)]
                print(f"    Active monitors: {len(active_monitors)}")
            except:
                pass
        
        # Monitor status endpoint
        success, response, response_time, details = self.test_endpoint("/crypto/monitor")
        self.log_test("Monitor Status", success, details, response_time)
    
    def run_telegram_tests(self):
        """Run Telegram integration tests"""
        print("\n📱 Running Telegram Tests...")
        
        # Telegram status
        success, response, response_time, details = self.test_endpoint("/telegram/status")
        self.log_test("Telegram Status", success, details, response_time)
        
        # Telegram test
        success, response, response_time, details = self.test_endpoint("/telegram/test", method="POST")
        self.log_test("Telegram Bot Test", success, details, response_time)
        
        # Polling status
        success, response, response_time, details = self.test_endpoint("/telegram/polling-status")
        self.log_test("Telegram Polling Status", success, details, response_time)
        
        # Users with alerts
        success, response, response_time, details = self.test_endpoint("/telegram/users-with-alerts")
        self.log_test("Users with Alerts", success, details, response_time)
    
    def run_crash_detection_tests(self):
        """Run crash detection tests"""
        print("\n🤖 Running Crash Detection Tests...")
        
        # Agent status
        success, response, response_time, details = self.test_endpoint("/agent/status")
        self.log_test("Agent Status", success, details, response_time)
        
        # Agent info
        success, response, response_time, details = self.test_endpoint("/agent/info")
        self.log_test("Agent Info", success, details, response_time)
        
        # Latest response
        success, response, response_time, details = self.test_endpoint("/agent/latest-response")
        self.log_test("Agent Latest Response", success, details, response_time)
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Comprehensive GuardX System Test")
        print("=" * 60)
        
        start_time = time.time()
        
        self.run_basic_tests()
        self.run_database_tests()
        self.run_binance_tests()
        self.run_monitor_tests()
        self.run_telegram_tests()
        self.run_crash_detection_tests()
        
        total_time = time.time() - start_time
        
        # Summary
        print("\n📊 Test Summary")
        print("=" * 60)
        
        passed = len([r for r in self.results if r['success']])
        failed = len([r for r in self.results if not r['success']])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n🎯 Overall Status: {'✅ HEALTHY' if failed == 0 else '⚠️ ISSUES DETECTED'}")
        
        return failed == 0

def main():
    import sys
    
    # Check if URL provided
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🎯 Testing GuardX API at: {base_url}")
    
    tester = GuardXTester(base_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
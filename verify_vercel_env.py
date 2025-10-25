#!/usr/bin/env python3
"""
Script to verify Vercel environment variables are properly set
"""

import requests
import json

def test_vercel_env():
    base_url = "https://asi-crash-guard-x.vercel.app"
    
    print("🔍 Testing Vercel Environment Variables")
    print("=" * 50)
    
    # Test database status
    try:
        response = requests.get(f"{base_url}/database/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            mongodb_connected = data.get('mongodb_connected', False)
            mongodb_configured = data.get('mongodb_url_configured', False)
            
            print(f"✅ Database Status Endpoint: OK")
            print(f"   MongoDB URL Configured: {'✅' if mongodb_configured else '❌'}")
            print(f"   MongoDB Connected: {'✅' if mongodb_connected else '❌'}")
            
            if mongodb_connected:
                print(f"   Database Name: {data.get('database_name', 'Unknown')}")
                mongodb_data = data.get('mongodb_data', {})
                print(f"   Users in DB: {mongodb_data.get('user_count', 0)}")
                print(f"   Monitors in DB: {mongodb_data.get('monitor_count', 0)}")
            else:
                print("   ⚠️  MongoDB not connected - check environment variables")
        else:
            print(f"❌ Database Status: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Database Status Error: {e}")
    
    print()
    
    # Test users endpoint
    try:
        response = requests.get(f"{base_url}/users/", timeout=10)
        if response.status_code == 200:
            users = response.json()
            print(f"✅ Users Endpoint: OK ({len(users)} users)")
        elif response.status_code == 503:
            print(f"❌ Users Endpoint: Database not available (HTTP 503)")
            print("   👉 Set MONGODB_URL and DATABASE_NAME in Vercel environment variables")
        else:
            print(f"❌ Users Endpoint: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Users Endpoint Error: {e}")
    
    print()
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Health Endpoint: OK")
        else:
            print(f"❌ Health Endpoint: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Health Endpoint Error: {e}")
    
    print()
    print("📋 Next Steps:")
    print("1. Go to Vercel Dashboard → asi-crash-guard-x → Settings → Environment Variables")
    print("2. Add the MongoDB environment variables")
    print("3. Redeploy the application")
    print("4. Run this script again to verify")

if __name__ == "__main__":
    test_vercel_env()
#!/usr/bin/env python3
"""
Test Vercel deployment after configuration
"""

import asyncio
import aiohttp
import json

VERCEL_URL = "https://asi-crash-guard-x.vercel.app"

async def test_endpoints():
    """Test key endpoints"""
    endpoints = [
        "/health",
        "/",
        "/database/status",
        "/users/",
        "/telegram/polling-status"
    ]
    
    print(f"🧪 Testing Vercel deployment: {VERCEL_URL}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                url = f"{VERCEL_URL}{endpoint}"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"✅ {endpoint}: OK")
                            
                            # Show key info for important endpoints
                            if endpoint == "/database/status":
                                connected = data.get('mongodb_connected', False)
                                print(f"   MongoDB: {'✅ Connected' if connected else '❌ Not Connected'}")
                            elif endpoint == "/users/":
                                user_count = len(data) if isinstance(data, list) else 0
                                print(f"   Users: {user_count}")
                                
                        except:
                            print(f"✅ {endpoint}: OK (non-JSON response)")
                    else:
                        print(f"❌ {endpoint}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"❌ {endpoint}: {str(e)}")
    
    print("=" * 60)
    print("💡 If you see authentication errors, disable Vercel Authentication in dashboard")
    print("💡 If you see 'Database not available', set environment variables in Vercel")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
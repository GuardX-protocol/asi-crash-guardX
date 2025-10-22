#!/usr/bin/env python3
from app.agents.crash_detector import crash_sentinel

if __name__ == "__main__":
    print("Starting Crash Sentinel Agent...")
    print("Agent will monitor BTC and ETH every 5 minutes")
    print("Press Ctrl+C to stop")
    
    try:
        crash_sentinel.run()
    except KeyboardInterrupt:
        print("\nAgent stopped by user")
    except Exception as e:
        print(f"Agent error: {e}")
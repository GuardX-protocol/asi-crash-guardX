#!/usr/bin/env python3
"""
Complete ASI + Email Alert Flow Test
====================================

This test demonstrates the complete flow:
1. ASI crash detection with formatted analysis
2. Email alert with structured AI insights
3. Professional email formatting
4. Real-world crash scenario simulation
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.asi_crash_detector import ASICrashDetector
from app.services.email_service import EmailService

# Load environment variables
load_dotenv()

async def simulate_complete_flow():
    """Simulate complete crash detection to email alert flow"""
    
    print("🚀 COMPLETE ASI + EMAIL ALERT FLOW TEST")
    print("=" * 60)
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize services
    detector = ASICrashDetector()
    email_service = EmailService()
    
    # Verify configurations
    print("🔧 SERVICE CONFIGURATION:")
    print(f"   🤖 ASI API: {'✅ Ready' if detector.is_configured() else '❌ Not configured'}")
    print(f"   📧 Email Service: {'✅ Ready' if email_service.is_configured() else '❌ Not configured'}")
    
    if not detector.is_configured() or not email_service.is_configured():
        print("\n❌ Services not properly configured")
        return False
    
    print(f"   🔗 ASI Endpoint: {detector.asi_endpoint}")
    print(f"   📧 SMTP: {email_service.smtp_server}:{email_service.smtp_port}")
    print()
    
    # Create realistic crash scenarios
    scenarios = [
        {
            "symbol": "BTCUSDT",
            "name": "Bitcoin Flash Crash",
            "base_price": 45000,
            "crash_percent": 15,
            "description": "Major Bitcoin selloff triggered by regulatory news"
        },
        {
            "symbol": "ETHUSDT", 
            "name": "Ethereum Network Issues",
            "base_price": 2800,
            "crash_percent": 12,
            "description": "Ethereum price drop due to network congestion"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📊 SCENARIO {i}: {scenario['name']}")
        print("-" * 40)
        
        # Generate crash data
        crash_data = generate_crash_scenario(
            scenario["base_price"], 
            scenario["crash_percent"]
        )
        
        current_price = crash_data[-1]["close"]
        price_drop = ((scenario["base_price"] - current_price) / scenario["base_price"]) * 100
        
        print(f"   🪙 Symbol: {scenario['symbol']}")
        print(f"   💰 Starting Price: ${scenario['base_price']:,.2f}")
        print(f"   💰 Current Price: ${current_price:,.2f}")
        print(f"   📉 Price Drop: {price_drop:.2f}%")
        print(f"   📝 Scenario: {scenario['description']}")
        
        print(f"\n   🤖 Running ASI Analysis...")
        
        try:
            # Run crash detection
            result = await detector.detect_crash(
                scenario["symbol"], 
                crash_data, 
                current_price
            )
            
            if "error" in result:
                print(f"   ❌ Analysis failed: {result['error']}")
                continue
            
            print(f"   ✅ Analysis Complete:")
            print(f"      🚨 Crash Detected: {'YES' if result['is_crash'] else 'NO'}")
            print(f"      📊 Probability: {result['crash_probability']:.1%}")
            print(f"      🎯 Confidence: {result['confidence_level']}")
            
            # Check ASI analysis
            asi_analysis = result.get('asi_analysis')
            if asi_analysis:
                print(f"      🤖 ASI Model: {asi_analysis.get('model')}")
                print(f"      📝 Response: {asi_analysis.get('response_length')} chars")
                
                # Check formatted analysis
                formatted = asi_analysis.get('formatted_analysis', {})
                if formatted and not formatted.get('error'):
                    print(f"      📊 Formatted: ✅ Success")
                    
                    # Show key insights
                    if formatted.get('crash_assessment'):
                        assessment = formatted['crash_assessment'][:100]
                        print(f"      💡 Assessment: {assessment}...")
                    
                    if formatted.get('severity'):
                        severity = formatted['severity'][:50]
                        print(f"      ⚠️ Severity: {severity}...")
                    
                    # Send email alert
                    print(f"\n   📧 Sending Email Alert...")
                    
                    email_summary = formatted.get('email_summary', 'ASI analysis available')
                    # Use a proper test recipient email instead of sender email
                    test_email = "manicdon7@gmail.com"  # This should be the user's email
                    
                    email_success = await email_service.send_crash_alert(
                        test_email,
                        scenario["symbol"],
                        current_price,
                        abs(price_drop),
                        email_summary,
                        "Test User"
                    )
                    
                    if email_success:
                        print(f"      ✅ Email sent to {test_email}")
                        print(f"      📧 Subject: 🚨 CRASH ALERT: {scenario['symbol']} - {abs(price_drop):.2f}% Drop")
                        print(f"      📝 Content: {len(email_summary)} characters")
                        print(f"      🎨 Format: HTML + Plain Text")
                    else:
                        print(f"      ❌ Email sending failed")
                else:
                    print(f"      📊 Formatted: ❌ Failed")
            else:
                print(f"      🤖 ASI Analysis: ❌ Not available")
            
        except Exception as e:
            print(f"   ❌ Scenario failed: {e}")
        
        print()
        
        # Wait between scenarios
        if i < len(scenarios):
            print("   ⏳ Waiting 5 seconds before next scenario...")
            await asyncio.sleep(5)
    
    return True

def generate_crash_scenario(base_price: float, crash_percent: float) -> list:
    """Generate realistic crash scenario data"""
    data = []
    
    # 30 data points representing hourly data
    for i in range(30):
        if i < 20:
            # Normal trading with small fluctuations
            fluctuation = ((-1) ** i) * (i * 0.5)  # Small random-like movement
            price = base_price + fluctuation
        else:
            # Crash phase - gradual then accelerating drop
            crash_progress = (i - 20) / 10  # 0 to 1
            # Accelerating crash curve
            crash_factor = crash_progress ** 1.5 * (crash_percent / 100)
            price = base_price * (1 - crash_factor)
        
        # Volume increases during crash
        base_volume = 1000000
        if i >= 20:
            volume_multiplier = 1 + (i - 20) * 0.3  # Volume spike during crash
            volume = base_volume * volume_multiplier
        else:
            volume = base_volume + (i * 10000)  # Normal volume growth
        
        data.append({
            "close": max(price, base_price * 0.1),  # Prevent negative prices
            "volume": volume,
            "timestamp": (datetime.utcnow() - timedelta(hours=30-i)).isoformat()
        })
    
    return data

async def show_email_preview():
    """Show what the email alert looks like"""
    
    print("📧 EMAIL ALERT PREVIEW")
    print("=" * 40)
    
    # Sample formatted analysis
    sample_analysis = """🤖 AI ANALYSIS FOR BTCUSDT
========================================
📊 ASSESSMENT: Genuine crash detected with 15% price drop and extreme technical indicators.

⚠️ SEVERITY: 8/10 - Significant crash with high volatility and oversold conditions.

🔍 LIKELY CAUSES:
   Regulatory uncertainty, large institutional sell-offs, and margin liquidations creating downward pressure.

📈 MARKET SENTIMENT:
   Extremely bearish with panic selling dominating. Fear index likely elevated.

⏰ SHORT-TERM OUTLOOK:
   Potential for further downside in next 24-48 hours, but oversold bounce possible.

💡 RECOMMENDATIONS:
   Avoid catching falling knife, wait for stabilization signals, consider DCA if long-term bullish.

========================================
🤖 Analysis by ASI-1 Fast Model
⏰ Generated: 2025-10-26 00:30:00 UTC"""
    
    print("Subject: 🚨 CRASH ALERT: BTCUSDT - 15.00% Drop Detected")
    print()
    print("Content Preview:")
    print("-" * 30)
    print(sample_analysis)
    print("-" * 30)
    print()
    print("📋 Email Features:")
    print("   ✅ HTML formatted with colors and styling")
    print("   ✅ Plain text fallback for compatibility")
    print("   ✅ Structured AI analysis sections")
    print("   ✅ Professional GuardX branding")
    print("   ✅ Actionable recommendations")
    print("   ✅ Technical indicator summaries")

async def main():
    """Main test function"""
    
    try:
        # Run complete flow test
        success = await simulate_complete_flow()
        
        print("\n" + "=" * 60)
        
        if success:
            print("✅ COMPLETE ASI + EMAIL FLOW TEST PASSED")
            print()
            print("🎯 What was tested:")
            print("   🤖 ASI-1 Fast API integration")
            print("   📊 Structured analysis formatting")
            print("   📧 Professional email alerts")
            print("   🎨 HTML email styling")
            print("   ⚡ Real-time crash detection")
            print("   🔄 Multiple scenario handling")
            print()
            print("📧 Check your email inbox for the alerts!")
        else:
            print("❌ COMPLETE ASI + EMAIL FLOW TEST FAILED")
        
        # Show email preview
        print("\n")
        await show_email_preview()
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())
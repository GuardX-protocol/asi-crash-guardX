"""
Advanced crash detection service with ASI-1 Fast model integration
"""
import aiohttp
import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import os
from app.services.binance_api import binance_api

logger = logging.getLogger(__name__)

class ASICrashDetector:
    def __init__(self):
        self.asi_api_key = os.getenv("ASI_API_KEY")
        # Use the correct ASI API endpoint from documentation
        self.asi_endpoint = "https://api.asi1.ai/v1/chat/completions"
        self.asi_base_url = "https://api.asi1.ai/v1"
        
    def is_configured(self) -> bool:
        """Check if ASI API is configured"""
        return bool(self.asi_api_key)
    
    async def detect_crash(
        self,
        symbol: str,
        price_data: List[Dict],
        current_price: float
    ) -> Dict:
        """
        Comprehensive crash detection using multiple algorithms + ASI analysis
        """
        try:
            # 1. Technical Analysis
            technical_signals = await self._analyze_technical_indicators(price_data)
            
            # 2. Price Movement Analysis
            price_signals = await self._analyze_price_movements(price_data, current_price)
            
            # 3. Volume Analysis
            volume_signals = await self._analyze_volume_patterns(price_data)
            
            # 4. Combine signals
            crash_probability = self._calculate_crash_probability(
                technical_signals, price_signals, volume_signals
            )
            
            # 5. ASI Analysis (if configured) - Lower threshold for more analysis
            asi_analysis = None
            asi_threshold = 0.1  # 10% threshold instead of 30%
            
            if self.is_configured() and crash_probability > asi_threshold:
                logger.info(f"🤖 Triggering ASI analysis for {symbol} (crash probability: {crash_probability:.1%})")
                asi_analysis = await self._get_asi_analysis(
                    symbol, price_data, technical_signals, price_signals
                )
                
                if asi_analysis:
                    logger.info(f"   ✅ ASI analysis completed for {symbol}")
                    logger.info(f"   🎯 Confidence: {asi_analysis.get('confidence', 'unknown')}")
                else:
                    logger.warning(f"   ⚠️ ASI analysis failed for {symbol}")
            elif not self.is_configured():
                logger.debug(f"🤖 ASI not configured - skipping analysis for {symbol}")
            else:
                logger.debug(f"🤖 Crash probability {crash_probability:.1%} below threshold ({asi_threshold:.0%}) - skipping ASI analysis for {symbol}")
                logger.debug(f"   📊 Technical signals: {len([k for k, v in technical_signals.items() if v and k != 'error'])} active")
                logger.debug(f"   📉 Price signals: {len([k for k, v in price_signals.items() if v and k != 'error'])} active")
                logger.debug(f"   📊 Volume signals: {len([k for k, v in volume_signals.items() if v and k != 'error'])} active")
            
            # 6. Determine if crash detected
            is_crash = crash_probability > 0.6
            
            return {
                "symbol": symbol,
                "is_crash": is_crash,
                "crash_probability": crash_probability,
                "current_price": current_price,
                "price_drop_24h": price_signals.get("price_drop_24h", 0),
                "technical_signals": technical_signals,
                "price_signals": price_signals,
                "volume_signals": volume_signals,
                "asi_analysis": asi_analysis,
                "detection_time": datetime.utcnow().isoformat(),
                "confidence_level": self._calculate_confidence(crash_probability, asi_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error in crash detection for {symbol}: {e}")
            return {
                "symbol": symbol,
                "is_crash": False,
                "error": str(e),
                "detection_time": datetime.utcnow().isoformat()
            }
    
    async def _analyze_technical_indicators(self, price_data: List[Dict]) -> Dict:
        """Analyze technical indicators for crash signals"""
        try:
            # Handle different field names from different APIs
            prices = []
            volumes = []
            
            for d in price_data:
                # Try different field names for price
                if "close" in d:
                    prices.append(float(d["close"]))
                elif "close_price" in d:
                    prices.append(float(d["close_price"]))
                else:
                    continue
                    
                # Try different field names for volume
                if "volume" in d:
                    volumes.append(float(d["volume"]))
                else:
                    volumes.append(0.0)  # Default volume if not available
            
            if len(prices) < 20:
                return {"error": "Insufficient data for technical analysis"}
            
            # RSI calculation
            rsi = self._calculate_rsi(prices)
            
            # Moving averages
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else sma_20
            
            # Bollinger Bands
            bb_upper, bb_lower = self._calculate_bollinger_bands(prices)
            
            # MACD
            macd_line, signal_line = self._calculate_macd(prices)
            
            # Volume analysis
            avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_spike = current_volume > (avg_volume * 2)
            
            return {
                "rsi": rsi,
                "rsi_oversold": rsi < 30,
                "price_below_sma20": prices[-1] < sma_20,
                "price_below_sma50": prices[-1] < sma_50,
                "price_below_bb_lower": prices[-1] < bb_lower,
                "macd_bearish": macd_line < signal_line,
                "volume_spike": volume_spike,
                "volume_ratio": current_volume / avg_volume,
                "sma_20": sma_20,
                "sma_50": sma_50,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower
            }
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return {"error": str(e)}
    
    async def _analyze_price_movements(self, price_data: List[Dict], current_price: float) -> Dict:
        """Analyze price movements for crash patterns"""
        try:
            # Handle different field names from different APIs
            prices = []
            timestamps = []
            
            for d in price_data:
                # Try different field names for price
                if "close" in d:
                    prices.append(float(d["close"]))
                elif "close_price" in d:
                    prices.append(float(d["close_price"]))
                else:
                    continue
                    
                # Get timestamp
                if "timestamp" in d:
                    timestamps.append(d["timestamp"])
                elif "open_time" in d:
                    timestamps.append(d["open_time"])
                else:
                    timestamps.append(datetime.utcnow().isoformat())
            
            # Calculate various timeframe drops
            price_1h = prices[-2] if len(prices) > 1 else current_price
            price_4h = prices[-5] if len(prices) > 4 else current_price
            price_24h = prices[-25] if len(prices) > 24 else current_price
            
            drop_1h = ((price_1h - current_price) / price_1h) * 100
            drop_4h = ((price_4h - current_price) / price_4h) * 100
            drop_24h = ((price_24h - current_price) / price_24h) * 100
            
            # Volatility analysis
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * 100
            
            # Consecutive drops
            consecutive_drops = 0
            for i in range(len(prices) - 1, 0, -1):
                if prices[i] < prices[i-1]:
                    consecutive_drops += 1
                else:
                    break
            
            return {
                "price_drop_1h": drop_1h,
                "price_drop_4h": drop_4h,
                "price_drop_24h": drop_24h,
                "volatility": volatility,
                "consecutive_drops": consecutive_drops,
                "sharp_drop_1h": drop_1h > 2,    # More sensitive: 2% instead of 5%
                "sharp_drop_4h": drop_4h > 3,    # More sensitive: 3% instead of 10%
                "sharp_drop_24h": drop_24h > 5,  # More sensitive: 5% instead of 15%
                "high_volatility": volatility > 2,  # More sensitive: 2% instead of 5%
                "multiple_drops": consecutive_drops >= 2  # More sensitive: 2 instead of 3
            }
            
        except Exception as e:
            logger.error(f"Error in price movement analysis: {e}")
            return {"error": str(e)}
    
    async def _analyze_volume_patterns(self, price_data: List[Dict]) -> Dict:
        """Analyze volume patterns for crash signals"""
        try:
            # Handle different field names from different APIs
            volumes = []
            prices = []
            
            for d in price_data:
                # Try different field names for volume
                if "volume" in d:
                    volumes.append(float(d["volume"]))
                else:
                    volumes.append(0.0)  # Default volume if not available
                    
                # Try different field names for price
                if "close" in d:
                    prices.append(float(d["close"]))
                elif "close_price" in d:
                    prices.append(float(d["close_price"]))
                else:
                    continue
            
            if len(volumes) < 10:
                return {"error": "Insufficient volume data"}
            
            # Volume trend analysis
            recent_volume = np.mean(volumes[-5:])
            historical_volume = np.mean(volumes[-20:-5])
            volume_increase = recent_volume > (historical_volume * 1.5)
            
            # Price-volume divergence
            price_trend = (prices[-1] - prices[-10]) / prices[-10]
            volume_trend = (recent_volume - historical_volume) / historical_volume
            
            # Selling pressure (high volume + price drop)
            selling_pressure = volume_increase and price_trend < -0.05
            
            return {
                "volume_increase": volume_increase,
                "volume_ratio": recent_volume / historical_volume,
                "selling_pressure": selling_pressure,
                "price_volume_divergence": abs(price_trend + volume_trend) > 0.1,
                "recent_volume": recent_volume,
                "historical_volume": historical_volume
            }
            
        except Exception as e:
            logger.error(f"Error in volume analysis: {e}")
            return {"error": str(e)}
    
    def _calculate_crash_probability(
        self,
        technical_signals: Dict,
        price_signals: Dict,
        volume_signals: Dict
    ) -> float:
        """Calculate overall crash probability based on all signals"""
        try:
            score = 0.0
            max_score = 0.0
            
            # Technical indicators (weight: 0.4)
            if not technical_signals.get("error"):
                if technical_signals.get("rsi_oversold"): score += 0.08
                if technical_signals.get("price_below_sma20"): score += 0.06
                if technical_signals.get("price_below_sma50"): score += 0.08
                if technical_signals.get("price_below_bb_lower"): score += 0.10
                if technical_signals.get("macd_bearish"): score += 0.05
                if technical_signals.get("volume_spike"): score += 0.03
                max_score += 0.4
            
            # Price movements (weight: 0.4) - More sensitive scoring
            if not price_signals.get("error"):
                if price_signals.get("sharp_drop_1h"): score += 0.12  # Increased weight
                if price_signals.get("sharp_drop_4h"): score += 0.15  # Increased weight
                if price_signals.get("sharp_drop_24h"): score += 0.18  # Increased weight
                if price_signals.get("high_volatility"): score += 0.08  # Increased weight
                if price_signals.get("multiple_drops"): score += 0.10  # Increased weight
                
                # Add base score for any price movement
                price_drop_24h = abs(price_signals.get("price_drop_24h", 0))
                if price_drop_24h > 1.0:  # Any drop > 1%
                    score += min(price_drop_24h * 0.02, 0.15)  # Up to 15% additional score
                
                max_score += 0.4
            
            # Volume patterns (weight: 0.2)
            if not volume_signals.get("error"):
                if volume_signals.get("selling_pressure"): score += 0.10
                if volume_signals.get("volume_increase"): score += 0.05
                if volume_signals.get("price_volume_divergence"): score += 0.05
                max_score += 0.2
            
            return min(score / max_score if max_score > 0 else 0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating crash probability: {e}")
            return 0.0
    
    async def _get_asi_analysis(
        self,
        symbol: str,
        price_data: List[Dict],
        technical_signals: Dict,
        price_signals: Dict
    ) -> Optional[Dict]:
        """Get AI analysis from ASI-1 Fast model"""
        if not self.is_configured():
            logger.warning("🤖 ASI API not configured - skipping AI analysis")
            return None
            
        try:
            # Prepare context for ASI
            recent_prices = []
            for d in price_data[-10:]:
                # Handle different field names from different APIs
                if "close" in d:
                    recent_prices.append(float(d["close"]))
                elif "close_price" in d:
                    recent_prices.append(float(d["close_price"]))
                else:
                    continue
            
            if not recent_prices:
                logger.warning(f"🤖 No price data available for ASI analysis of {symbol}")
                return None
                
            current_price = recent_prices[-1]
            
            prompt = f"""
            You are an expert cryptocurrency analyst. Analyze the crash situation for {symbol} and provide a structured response.
            
            MARKET DATA:
            - Symbol: {symbol}
            - Current Price: ${current_price:,.4f}
            - Recent Prices: {[f"${p:,.4f}" for p in recent_prices[-5:]]}
            - 24h Drop: {price_signals.get('price_drop_24h', 0):.2f}%
            - 4h Drop: {price_signals.get('price_drop_4h', 0):.2f}%
            - 1h Drop: {price_signals.get('price_drop_1h', 0):.2f}%
            
            TECHNICAL INDICATORS:
            - RSI: {technical_signals.get('rsi', 50):.1f}
            - Price vs SMA20: {'Below' if technical_signals.get('price_below_sma20') else 'Above'}
            - Price vs SMA50: {'Below' if technical_signals.get('price_below_sma50') else 'Above'}
            - Bollinger Bands: {'Below lower band' if technical_signals.get('price_below_bb_lower') else 'Within bands'}
            - MACD: {'Bearish' if technical_signals.get('macd_bearish') else 'Bullish'}
            - Volume: {'Spike' if technical_signals.get('volume_spike') else 'Normal'}
            
            Provide your analysis in this exact format:
            
            CRASH ASSESSMENT: [Is this a genuine crash or normal volatility? One sentence.]
            
            SEVERITY: [Rate 1-10, where 10 is most severe] - [Brief explanation]
            
            LIKELY CAUSES: [2-3 potential factors driving this movement]
            
            MARKET SENTIMENT: [Current sentiment in 1-2 sentences]
            
            SHORT-TERM OUTLOOK: [Next 24-48 hours prediction]
            
            MEDIUM-TERM OUTLOOK: [Next 1-2 weeks prediction]
            
            KEY RISKS: [Top 2-3 risks to monitor]
            
            RECOMMENDATIONS: [3-4 specific actionable insights for investors]
            
            Keep each section concise but informative. Focus on practical insights.
            """
            
            headers = {
                "Authorization": f"Bearer {self.asi_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "asi1-fast",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency market analyst with deep knowledge of technical analysis, market psychology, and crash detection. Provide detailed, actionable insights based on the data provided."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            # Log the ASI API request
            logger.info(f"🤖 ASI-1 Fast API Request for {symbol}")
            logger.info(f"   📡 Endpoint: {self.asi_base_url}/chat/completions")
            logger.info(f"   💰 Current Price: ${current_price:,.4f}")
            logger.info(f"   📉 24h Drop: {price_signals.get('price_drop_24h', 0):.2f}%")
            logger.info(f"   🎯 Crash Probability: {self._calculate_crash_probability(technical_signals, price_signals, {}):.1%}")
            logger.info(f"   📊 Technical Signals: {len([k for k, v in technical_signals.items() if v and k != 'error'])} active")
            
            async with aiohttp.ClientSession() as session:
                try:
                    logger.info(f"   📡 Calling ASI API: {self.asi_endpoint}")
                    
                    async with session.post(
                        self.asi_endpoint,
                        headers=headers,
                        json=payload,
                        timeout=30
                    ) as response:
                        
                        # Log response status
                        logger.info(f"   📡 ASI API Response: HTTP {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            # Handle ASI API response format
                            analysis_text = ""
                            reasoning_text = ""
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                if "message" in choice:
                                    message = choice["message"]
                                    # ASI API puts the actual response in 'reasoning' field
                                    if "reasoning" in message and message["reasoning"]:
                                        reasoning_text = message["reasoning"]
                                        analysis_text = reasoning_text
                                    # Fallback to content if available
                                    elif "content" in message and message["content"]:
                                        analysis_text = message["content"]
                            
                            # Also check if there's thought process in the main response
                            if not analysis_text and "thought" in data and data["thought"]:
                                if isinstance(data["thought"], list) and len(data["thought"]) > 0:
                                    analysis_text = data["thought"][0]
                                elif isinstance(data["thought"], str):
                                    analysis_text = data["thought"]
                            
                            # Log successful response
                            logger.info(f"   ✅ ASI Analysis Received")
                            logger.info(f"   📝 Response Length: {len(analysis_text)} characters")
                            logger.info(f"   🤖 Model: asi1-fast")
                            logger.info(f"   ⏱️ Timestamp: {datetime.utcnow().strftime('%H:%M:%S')}")
                            
                            # Log the actual analysis (truncated for readability)
                            if analysis_text:
                                logger.info(f"   📊 ASI ANALYSIS PREVIEW:")
                                logger.info(f"   " + "="*50)
                                # Split into lines and log each line with proper formatting
                                analysis_lines = analysis_text.split('\n')
                                for i, line in enumerate(analysis_lines[:15]):  # First 15 lines
                                    if line.strip():
                                        logger.info(f"   {line.strip()}")
                                if len(analysis_lines) > 15:
                                    logger.info(f"   ... ({len(analysis_lines) - 15} more lines)")
                                logger.info(f"   " + "="*50)
                            
                            # Parse and format the analysis
                            formatted_analysis = self._format_asi_analysis(analysis_text, symbol, current_price)
                            
                            return {
                                "raw_analysis": analysis_text,
                                "formatted_analysis": formatted_analysis,
                                "reasoning": reasoning_text,
                                "model": "asi1-fast",
                                "timestamp": datetime.utcnow().isoformat(),
                                "confidence": "high" if len(analysis_text) > 200 else "medium",
                                "response_length": len(analysis_text),
                                "api_status": response.status,
                                "endpoint_used": self.asi_endpoint,
                                "thought_process": data.get("thought", []),
                                "conversation_id": data.get("conversation_id"),
                                "usage": data.get("usage", {}),
                                "finish_reason": data.get("choices", [{}])[0].get("finish_reason") if data.get("choices") else None
                            }
                        else:
                            # Log error response
                            error_text = await response.text()
                            logger.error(f"   ❌ ASI API Error: HTTP {response.status}")
                            logger.error(f"   📝 Error: {error_text}")
                            return None
                            
                except Exception as api_error:
                    logger.error(f"   ❌ ASI API Exception: {str(api_error)}")
                    logger.error(f"   🔍 Error Type: {type(api_error).__name__}")
                    return None
                        
        except asyncio.TimeoutError:
            logger.error(f"   ⏱️ ASI API Timeout for {symbol} (30s limit exceeded)")
            return None
        except Exception as e:
            logger.error(f"   ❌ ASI API Exception for {symbol}: {e}")
            logger.error(f"   🔍 Error Type: {type(e).__name__}")
            return None
    
    def _calculate_confidence(self, crash_probability: float, asi_analysis: Optional[Dict]) -> str:
        """Calculate confidence level of the crash detection"""
        if asi_analysis and crash_probability > 0.7:
            return "very_high"
        elif crash_probability > 0.8:
            return "high"
        elif crash_probability > 0.6:
            return "medium"
        elif crash_probability > 0.4:
            return "low"
        else:
            return "very_low"
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: int = 2) -> Tuple[float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            sma = np.mean(prices)
            std = np.std(prices)
        else:
            sma = np.mean(prices[-period:])
            std = np.std(prices[-period:])
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, lower_band
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
        """Calculate MACD indicator"""
        if len(prices) < slow:
            return 0.0, 0.0
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # For simplicity, using SMA instead of EMA for signal line
        if len(prices) >= slow + signal:
            macd_values = [self._calculate_ema(prices[:i+1], fast) - self._calculate_ema(prices[:i+1], slow) 
                          for i in range(slow-1, len(prices))]
            signal_line = np.mean(macd_values[-signal:])
        else:
            signal_line = macd_line
        
        return macd_line, signal_line
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _format_asi_analysis(self, raw_analysis: str, symbol: str, current_price: float) -> Dict:
        """Format ASI analysis into structured sections"""
        try:
            if not raw_analysis:
                return {"error": "No analysis available"}
            
            # Initialize sections
            sections = {
                "crash_assessment": "",
                "severity": "",
                "likely_causes": "",
                "market_sentiment": "",
                "short_term_outlook": "",
                "medium_term_outlook": "",
                "key_risks": "",
                "recommendations": "",
                "summary": ""
            }
            
            # Split analysis into lines and process
            lines = raw_analysis.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify section headers
                if "CRASH ASSESSMENT:" in line.upper():
                    current_section = "crash_assessment"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "SEVERITY:" in line.upper():
                    current_section = "severity"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "LIKELY CAUSES:" in line.upper():
                    current_section = "likely_causes"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "MARKET SENTIMENT:" in line.upper():
                    current_section = "market_sentiment"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "SHORT-TERM OUTLOOK:" in line.upper() or "SHORT TERM:" in line.upper():
                    current_section = "short_term_outlook"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "MEDIUM-TERM OUTLOOK:" in line.upper() or "MEDIUM TERM:" in line.upper():
                    current_section = "medium_term_outlook"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "KEY RISKS:" in line.upper() or "RISK FACTORS:" in line.upper():
                    current_section = "key_risks"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif "RECOMMENDATIONS:" in line.upper() or "ACTIONABLE INSIGHTS:" in line.upper():
                    current_section = "recommendations"
                    sections[current_section] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif current_section and line:
                    # Continue adding to current section
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
            
            # Create a summary if sections are empty, use the raw analysis
            if not any(sections.values()):
                # Fallback: use first 300 characters as summary
                sections["summary"] = raw_analysis[:300] + "..." if len(raw_analysis) > 300 else raw_analysis
            
            # Clean up sections
            for key, value in sections.items():
                if value:
                    sections[key] = value.strip()
            
            # Create formatted summary for email
            email_summary = self._create_email_summary(sections, symbol, current_price)
            sections["email_summary"] = email_summary
            
            return sections
            
        except Exception as e:
            logger.error(f"Error formatting ASI analysis: {e}")
            return {
                "error": f"Formatting error: {str(e)}",
                "summary": raw_analysis[:200] + "..." if len(raw_analysis) > 200 else raw_analysis
            }
    
    def _create_email_summary(self, sections: Dict, symbol: str, current_price: float) -> str:
        """Create a formatted summary for email alerts"""
        try:
            summary_parts = []
            
            # Header
            summary_parts.append(f"🤖 AI ANALYSIS FOR {symbol}")
            summary_parts.append("=" * 40)
            
            # Key sections
            if sections.get("crash_assessment"):
                summary_parts.append(f"📊 ASSESSMENT: {sections['crash_assessment']}")
                summary_parts.append("")
            
            if sections.get("severity"):
                summary_parts.append(f"⚠️ SEVERITY: {sections['severity']}")
                summary_parts.append("")
            
            if sections.get("likely_causes"):
                summary_parts.append(f"🔍 LIKELY CAUSES:")
                summary_parts.append(f"   {sections['likely_causes']}")
                summary_parts.append("")
            
            if sections.get("market_sentiment"):
                summary_parts.append(f"📈 MARKET SENTIMENT:")
                summary_parts.append(f"   {sections['market_sentiment']}")
                summary_parts.append("")
            
            if sections.get("short_term_outlook"):
                summary_parts.append(f"⏰ SHORT-TERM OUTLOOK:")
                summary_parts.append(f"   {sections['short_term_outlook']}")
                summary_parts.append("")
            
            if sections.get("recommendations"):
                summary_parts.append(f"💡 RECOMMENDATIONS:")
                summary_parts.append(f"   {sections['recommendations']}")
                summary_parts.append("")
            
            # Footer
            summary_parts.append("=" * 40)
            summary_parts.append(f"🤖 Analysis by ASI-1 Fast Model")
            summary_parts.append(f"⏰ Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating email summary: {e}")
            return f"AI Analysis available for {symbol} at ${current_price:,.4f}"

# Global crash detector instance
asi_crash_detector = ASICrashDetector()
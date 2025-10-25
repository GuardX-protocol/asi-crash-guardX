"""
Binance API Service - Real-time cryptocurrency price fetching
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class BinanceAPIService:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.price_cache = {}
        self.cache_timestamp = {}
        self.cache_duration = 30  # seconds
        
    async def get_symbol_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a single symbol"""
        try:
            # Ensure symbol has USDT suffix
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"
            
            # Check cache first
            if self._is_cached(symbol):
                return self.price_cache[symbol]
            
            url = f"{self.base_url}/ticker/24hr"
            params = {"symbol": symbol}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        price_data = {
                            "symbol": symbol,
                            "price": float(data["lastPrice"]),
                            "change_24h": float(data["priceChangePercent"]),
                            "volume_24h": float(data["volume"]),
                            "high_24h": float(data["highPrice"]),
                            "low_24h": float(data["lowPrice"]),
                            "open_price": float(data["openPrice"]),
                            "close_price": float(data["lastPrice"]),
                            "timestamp": datetime.utcnow().isoformat(),
                            "source": "binance"
                        }
                        
                        # Cache the result
                        self._cache_price(symbol, price_data)
                        return price_data
                    else:
                        logger.warning(f"Binance API error for {symbol}: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get prices for multiple symbols efficiently"""
        try:
            # Ensure all symbols have USDT suffix
            formatted_symbols = []
            for symbol in symbols:
                if not symbol.endswith('USDT'):
                    formatted_symbols.append(f"{symbol}USDT")
                else:
                    formatted_symbols.append(symbol)
            
            # Check cache for all symbols
            cached_results = {}
            uncached_symbols = []
            
            for symbol in formatted_symbols:
                if self._is_cached(symbol):
                    cached_results[symbol] = self.price_cache[symbol]
                else:
                    uncached_symbols.append(symbol)
            
            # If all symbols are cached, return cached results
            if not uncached_symbols:
                return cached_results
            
            # Fetch uncached symbols
            url = f"{self.base_url}/ticker/24hr"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        all_data = await response.json()
                        
                        # Filter for requested symbols
                        results = cached_results.copy()
                        
                        for item in all_data:
                            symbol = item["symbol"]
                            if symbol in uncached_symbols:
                                price_data = {
                                    "symbol": symbol,
                                    "price": float(item["lastPrice"]),
                                    "change_24h": float(item["priceChangePercent"]),
                                    "volume_24h": float(item["volume"]),
                                    "high_24h": float(item["highPrice"]),
                                    "low_24h": float(item["lowPrice"]),
                                    "open_price": float(item["openPrice"]),
                                    "close_price": float(item["lastPrice"]),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "binance"
                                }
                                
                                results[symbol] = price_data
                                self._cache_price(symbol, price_data)
                        
                        return results
                    else:
                        logger.warning(f"Binance API error: {response.status}")
                        return cached_results
                        
        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            return {}
    
    async def get_top_symbols(self, limit: int = 50) -> Dict[str, Dict[str, Any]]:
        """Get top symbols by volume"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        all_data = await response.json()
                        
                        # Filter USDT pairs and sort by volume
                        usdt_pairs = [
                            item for item in all_data 
                            if item["symbol"].endswith("USDT") and 
                            item["symbol"] not in ["USDCUSDT", "BUSDUSDT", "TUSDUSDT"]
                        ]
                        
                        # Sort by volume (descending)
                        usdt_pairs.sort(key=lambda x: float(x["volume"]), reverse=True)
                        
                        # Take top symbols
                        top_symbols = usdt_pairs[:limit]
                        
                        results = {}
                        for item in top_symbols:
                            symbol = item["symbol"]
                            price_data = {
                                "symbol": symbol,
                                "price": float(item["lastPrice"]),
                                "change_24h": float(item["priceChangePercent"]),
                                "volume_24h": float(item["volume"]),
                                "high_24h": float(item["highPrice"]),
                                "low_24h": float(item["lowPrice"]),
                                "open_price": float(item["openPrice"]),
                                "close_price": float(item["lastPrice"]),
                                "timestamp": datetime.utcnow().isoformat(),
                                "source": "binance"
                            }
                            
                            results[symbol] = price_data
                            self._cache_price(symbol, price_data)
                        
                        return results
                    else:
                        logger.warning(f"Binance API error: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error fetching top symbols: {e}")
            return {}
    
    async def get_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical kline/candlestick data"""
        try:
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"
            
            url = f"{self.base_url}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        klines = []
                        for item in data:
                            kline = {
                                "open_time": int(item[0]),
                                "open_price": float(item[1]),
                                "high_price": float(item[2]),
                                "low_price": float(item[3]),
                                "close_price": float(item[4]),
                                "volume": float(item[5]),
                                "close_time": int(item[6]),
                                "quote_volume": float(item[7]),
                                "trades_count": int(item[8]),
                                "taker_buy_base_volume": float(item[9]),
                                "taker_buy_quote_volume": float(item[10]),
                                "timestamp": datetime.fromtimestamp(int(item[0]) / 1000).isoformat()
                            }
                            klines.append(kline)
                        
                        return klines
                    else:
                        logger.warning(f"Binance klines API error for {symbol}: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def _is_cached(self, symbol: str) -> bool:
        """Check if symbol price is cached and still valid"""
        if symbol not in self.price_cache or symbol not in self.cache_timestamp:
            return False
        
        cache_age = (datetime.utcnow() - self.cache_timestamp[symbol]).total_seconds()
        return cache_age < self.cache_duration
    
    def _cache_price(self, symbol: str, price_data: Dict[str, Any]):
        """Cache price data"""
        self.price_cache[symbol] = price_data
        self.cache_timestamp[symbol] = datetime.utcnow()
    
    def clear_cache(self):
        """Clear all cached data"""
        self.price_cache.clear()
        self.cache_timestamp.clear()
        logger.info("🗑️ Binance API cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_symbols": len(self.price_cache),
            "cache_duration_seconds": self.cache_duration,
            "oldest_cache": min(self.cache_timestamp.values()).isoformat() if self.cache_timestamp else None,
            "newest_cache": max(self.cache_timestamp.values()).isoformat() if self.cache_timestamp else None
        }

# Global instance
binance_api = BinanceAPIService()
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from app.database import is_connected
from app.models import User, Monitor, MonitorAlert
from app.models import (
    TokenPrice, MonitorConfigRequest, MonitorConfigResponse, 
    MonitorStatusResponse
)
from datetime import datetime
import requests

router = APIRouter()

# Simple price cache
price_cache = {}
cache_timestamp = None

async def get_binance_prices(symbols: Optional[List[str]] = None):
    """Get prices from Binance API using the new service"""
    try:
        from app.services.binance_api import binance_api
        
        if symbols:
            # Get specific symbols
            price_data = await binance_api.get_multiple_prices(symbols)
            prices = {}
            for symbol, data in price_data.items():
                prices[symbol] = TokenPrice(
                    symbol=symbol,
                    price=data['price'],
                    change_24h=data['change_24h'],
                    volume_24h=data['volume_24h'],
                    market_cap=None,
                    timestamp=data['timestamp']
                )
            return prices
        else:
            # Get top symbols
            price_data = await binance_api.get_top_symbols(limit=50)
            prices = {}
            for symbol, data in price_data.items():
                prices[symbol] = TokenPrice(
                    symbol=symbol,
                    price=data['price'],
                    change_24h=data['change_24h'],
                    volume_24h=data['volume_24h'],
                    market_cap=None,
                    timestamp=data['timestamp']
                )
            return prices
    except Exception as e:
        logger.error(f"Error getting Binance prices: {e}")
        return {}

@router.get("/prices", response_model=Dict[str, TokenPrice])
async def get_crypto_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    limit: Optional[int] = Query(None, description="Limit number of results")
):
    try:
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        # Simple cache check
        global cache_timestamp, price_cache
        if cache_timestamp and (datetime.now() - cache_timestamp).seconds < 60:
            if symbol_list:
                cached_prices = {k: v for k, v in price_cache.items() if k in symbol_list}
                if cached_prices:
                    return cached_prices
            else:
                return price_cache
        
        prices = await get_binance_prices(symbol_list)
        
        # Update cache
        price_cache.update(prices)
        cache_timestamp = datetime.now()
        
        if limit:
            prices = dict(list(prices.items())[:limit])
        
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices/{symbol}")
async def get_single_crypto_price(symbol: str):
    try:
        import aiohttp
        
        symbol = symbol.upper()
        # Ensure USDT suffix
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
        
        # Try multiple API endpoints for better reliability
        endpoints = [
            f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}",
            f"https://api.binance.us/api/v3/ticker/24hr?symbol={symbol}",
            f"https://api1.binance.com/api/v3/ticker/24hr?symbol={symbol}",
            f"https://api2.binance.com/api/v3/ticker/24hr?symbol={symbol}",
            f"https://api3.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        ]
        
        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return TokenPrice(
                                symbol=symbol,
                                price=float(data['lastPrice']),
                                change_24h=float(data['priceChangePercent']),
                                volume_24h=float(data['volume']),
                                market_cap=None,
                                timestamp=datetime.utcnow().isoformat()
                            )
                        elif response.status == 451:
                            # Geo-blocked, try next endpoint
                            continue
                        else:
                            # Other error, try next endpoint
                            continue
                except Exception as e:
                    # Network error, try next endpoint
                    continue
            
            # If all endpoints fail, try CoinGecko as fallback
            try:
                # Convert BTCUSDT to bitcoin for CoinGecko
                coin_id = "bitcoin" if symbol.startswith("BTC") else "ethereum" if symbol.startswith("ETH") else None
                if coin_id:
                    coingecko_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
                    async with session.get(coingecko_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            coin_data = data.get(coin_id, {})
                            return TokenPrice(
                                symbol=symbol,
                                price=float(coin_data.get('usd', 0)),
                                change_24h=float(coin_data.get('usd_24h_change', 0)),
                                volume_24h=0,  # CoinGecko simple API doesn't include volume
                                market_cap=None,
                                timestamp=datetime.utcnow().isoformat()
                            )
            except Exception as e:
                pass
            
            # If everything fails
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found - all price sources unavailable")
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/create", response_model=MonitorConfigResponse)
async def create_monitor_config(config: MonitorConfigRequest):
    try:
        from app.database import ensure_connection
        
        # Ensure database connection
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Check if monitor already exists
        existing_monitor = await Monitor.find_one(Monitor.name == config.name)
        if existing_monitor:
            raise HTTPException(status_code=400, detail=f"Monitor '{config.name}' already exists")
        
        # Check if user exists
        user = await User.find_one(User.walletAddress == config.userId)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        interval_seconds = config.interval_seconds or 300
        
        # Create monitor
        monitor_data = {
            "name": config.name,
            "userId": config.userId,
            "symbols": [s.upper() for s in config.symbols],
            "interval_seconds": interval_seconds,
            "interval_str": config.interval_str or "5m",
            "price_change_threshold": config.price_change_threshold,
            "volume_change_threshold": config.volume_change_threshold,
            "crash_probability_threshold": config.crash_probability_threshold,
            "enabled": config.enabled,
            "alert_webhooks": config.alert_webhooks or [],
            "telegram_alerts": config.telegram_alerts,
            "email_alerts": config.email_alerts,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        new_monitor = Monitor(**monitor_data)
        await new_monitor.insert()
        
        return MonitorConfigResponse(
            name=new_monitor.name,
            userId=new_monitor.userId,
            symbols=new_monitor.symbols,
            interval_seconds=new_monitor.interval_seconds,
            interval_str=new_monitor.interval_str,
            price_change_threshold=new_monitor.price_change_threshold,
            volume_change_threshold=new_monitor.volume_change_threshold,
            crash_probability_threshold=new_monitor.crash_probability_threshold,
            enabled=new_monitor.enabled,
            alert_webhooks=new_monitor.alert_webhooks,
            telegram_alerts=new_monitor.telegram_alerts,
            email_alerts=new_monitor.email_alerts,
            running=False
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitors")
async def list_monitor_configs(user_id: Optional[str] = Query(None)):
    try:
        from app.database import ensure_connection
        
        # Ensure database connection
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database not available")
        
        if user_id:
            monitors = await Monitor.find(Monitor.userId == user_id).to_list()
        else:
            monitors = await Monitor.find_all().to_list()
        
        configs = []
        for monitor in monitors:
            configs.append(MonitorConfigResponse(
                name=monitor.name,
                userId=monitor.userId,
                symbols=monitor.symbols,
                interval_seconds=monitor.interval_seconds,
                interval_str=getattr(monitor, 'interval_str', '5m'),
                price_change_threshold=monitor.price_change_threshold,
                volume_change_threshold=monitor.volume_change_threshold,
                crash_probability_threshold=getattr(monitor, 'crash_probability_threshold', 60.0),
                enabled=monitor.enabled,
                alert_webhooks=monitor.alert_webhooks,
                telegram_alerts=getattr(monitor, 'telegram_alerts', False),
                email_alerts=getattr(monitor, 'email_alerts', False),
                running=monitor.enabled  # Simplified - running if enabled
            ))
        return configs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_alerts(
    user_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    try:
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        query = {}
        if user_id:
            query['userId'] = user_id
        if symbol:
            query['symbol'] = symbol.upper()
        if severity:
            query['severity'] = severity
        
        alerts = await MonitorAlert.find(query).limit(limit).to_list()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor", response_model=MonitorStatusResponse)
async def get_monitor_status():
    try:
        from app.database import ensure_connection
        
        # Ensure database connection
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database not available")
        
        monitors = await Monitor.find_all().to_list()
        active_monitors = [m for m in monitors if m.enabled]
        
        return MonitorStatusResponse(
            active_monitors=len(active_monitors),
            cached_tokens=len(price_cache),
            monitor_configs={m.name: {"enabled": m.enabled, "symbols": m.symbols} for m in monitors}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/monitor/{monitor_name}")
async def patch_monitor_config(monitor_name: str, monitor_patch: dict):
    """Partial update of monitor configuration"""
    try:
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Check if monitor exists
        existing_monitor = await Monitor.find_one(Monitor.name == monitor_name)
        if not existing_monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        # Only update provided fields
        update_fields = {k: v for k, v in monitor_patch.items() if v is not None}
        update_fields["updatedAt"] = datetime.utcnow()
        
        # Validate symbols if provided
        if "symbols" in update_fields:
            update_fields["symbols"] = [s.upper() for s in update_fields["symbols"]]
        
        await existing_monitor.update({"$set": update_fields})
        updated_monitor = await Monitor.find_one(Monitor.name == monitor_name)
        
        if not updated_monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        return MonitorConfigResponse(
            name=updated_monitor.name,
            userId=updated_monitor.userId,
            symbols=updated_monitor.symbols,
            interval_seconds=updated_monitor.interval_seconds,
            interval_str=getattr(updated_monitor, 'interval_str', '5m'),
            price_change_threshold=updated_monitor.price_change_threshold,
            volume_change_threshold=updated_monitor.volume_change_threshold,
            crash_probability_threshold=getattr(updated_monitor, 'crash_probability_threshold', 60.0),
            enabled=updated_monitor.enabled,
            alert_webhooks=updated_monitor.alert_webhooks,
            telegram_alerts=getattr(updated_monitor, 'telegram_alerts', False),
            email_alerts=getattr(updated_monitor, 'email_alerts', False),
            running=updated_monitor.enabled
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/monitor/{monitor_name}")
async def update_monitor_config(monitor_name: str, config: MonitorConfigRequest):
    """Full update of monitor configuration"""
    try:
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Check if monitor exists
        existing_monitor = await Monitor.find_one(Monitor.name == monitor_name)
        if not existing_monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        # Full update with all fields
        monitor_data = {
            "name": config.name,
            "userId": config.userId,
            "symbols": [s.upper() for s in config.symbols],
            "interval_seconds": config.interval_seconds or 300,
            "interval_str": config.interval_str or "5m",
            "price_change_threshold": config.price_change_threshold,
            "volume_change_threshold": config.volume_change_threshold,
            "crash_probability_threshold": config.crash_probability_threshold,
            "enabled": config.enabled,
            "alert_webhooks": config.alert_webhooks,
            "telegram_alerts": config.telegram_alerts,
            "email_alerts": config.email_alerts,
            "updatedAt": datetime.utcnow()
        }
        
        await existing_monitor.update({"$set": monitor_data})
        updated_monitor = await Monitor.find_one(Monitor.name == monitor_name)
        
        if not updated_monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        return MonitorConfigResponse(
            name=updated_monitor.name,
            userId=updated_monitor.userId,
            symbols=updated_monitor.symbols,
            interval_seconds=updated_monitor.interval_seconds,
            interval_str=getattr(updated_monitor, 'interval_str', '5m'),
            price_change_threshold=updated_monitor.price_change_threshold,
            volume_change_threshold=updated_monitor.volume_change_threshold,
            crash_probability_threshold=getattr(updated_monitor, 'crash_probability_threshold', 60.0),
            enabled=updated_monitor.enabled,
            alert_webhooks=updated_monitor.alert_webhooks,
            telegram_alerts=getattr(updated_monitor, 'telegram_alerts', False),
            email_alerts=getattr(updated_monitor, 'email_alerts', False),
            running=updated_monitor.enabled
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/monitor/{monitor_name}")
async def delete_monitor_config(monitor_name: str):
    """Delete monitor configuration"""
    try:
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        monitor = await Monitor.find_one(Monitor.name == monitor_name)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        await monitor.delete()
        
        return {"message": f"Monitor '{monitor_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/trigger")
async def trigger_monitoring():
    """Manually trigger monitoring for testing"""
    try:
        from app.services.monitor_service import monitor_service
        
        if not monitor_service.running:
            return {"error": "Monitor service is not running"}
        
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Get active monitors
        monitors = await Monitor.find(Monitor.enabled == True).to_list()
        
        if not monitors:
            return {"message": "No active monitors found"}
        
        # Process each monitor once
        results = []
        for monitor in monitors:
            try:
                await monitor_service._process_monitor(monitor)
                results.append({"monitor": monitor.name, "status": "processed"})
            except Exception as e:
                results.append({"monitor": monitor.name, "status": "error", "error": str(e)})
        
        return {
            "message": f"Triggered monitoring for {len(monitors)} monitor(s)",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/alerts/{alert_id}")
async def patch_alert(alert_id: str, alert_patch: dict):
    """Partial update of alert"""
    try:
        if not is_connected():
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Only update provided fields
        update_fields = {k: v for k, v in alert_patch.items() if v is not None}
        update_fields["updatedAt"] = datetime.utcnow()
        
        from bson import ObjectId
        alert = await MonitorAlert.find_one(MonitorAlert.id == ObjectId(alert_id))
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        await alert.update({"$set": update_fields})
        updated_alert = await MonitorAlert.find_one(MonitorAlert.id == ObjectId(alert_id))
        
        return updated_alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/binance/test")
async def test_binance_api():
    """Test Binance API connectivity and performance"""
    try:
        from app.services.binance_api import binance_api
        import time
        
        start_time = time.time()
        
        # Test single symbol
        btc_data = await binance_api.get_symbol_price("BTC")
        single_time = time.time() - start_time
        
        # Test multiple symbols
        start_time = time.time()
        multi_data = await binance_api.get_multiple_prices(["BTC", "ETH", "ADA"])
        multi_time = time.time() - start_time
        
        # Test top symbols
        start_time = time.time()
        top_data = await binance_api.get_top_symbols(limit=10)
        top_time = time.time() - start_time
        
        return {
            "binance_api_status": "✅ Working",
            "tests": {
                "single_symbol": {
                    "symbol": "BTCUSDT",
                    "price": btc_data['price'] if btc_data else None,
                    "response_time_ms": round(single_time * 1000, 2),
                    "success": bool(btc_data)
                },
                "multiple_symbols": {
                    "symbols_requested": 3,
                    "symbols_received": len(multi_data),
                    "response_time_ms": round(multi_time * 1000, 2),
                    "success": len(multi_data) > 0
                },
                "top_symbols": {
                    "symbols_requested": 10,
                    "symbols_received": len(top_data),
                    "response_time_ms": round(top_time * 1000, 2),
                    "success": len(top_data) > 0
                }
            },
            "cache_stats": binance_api.get_cache_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "binance_api_status": "❌ Error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/prices/realtime/{symbol}")
async def get_realtime_price(symbol: str):
    """Get real-time price with additional market data"""
    try:
        from app.services.binance_api import binance_api
        
        symbol = symbol.upper()
        
        # Get current price
        price_data = await binance_api.get_symbol_price(symbol)
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        # Get recent klines for trend analysis
        klines = await binance_api.get_klines(symbol, interval="1m", limit=10)
        
        # Calculate trend
        trend = "neutral"
        if len(klines) >= 2:
            recent_close = klines[-1]['close_price']
            previous_close = klines[-2]['close_price']
            if recent_close > previous_close:
                trend = "bullish"
            elif recent_close < previous_close:
                trend = "bearish"
        
        return {
            "symbol": price_data['symbol'],
            "current_price": price_data['price'],
            "change_24h": price_data['change_24h'],
            "volume_24h": price_data['volume_24h'],
            "high_24h": price_data['high_24h'],
            "low_24h": price_data['low_24h'],
            "trend": trend,
            "recent_candles": len(klines),
            "last_update": price_data['timestamp'],
            "source": "binance_realtime"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/prices/mock/{symbol}")
async def get_mock_crypto_price(symbol: str):
    """Get mock crypto price for testing when external APIs are unavailable"""
    try:
        symbol = symbol.upper()
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
        
        # Mock prices for common symbols
        mock_prices = {
            "BTCUSDT": {"price": 111500.00, "change_24h": 2.5},
            "ETHUSDT": {"price": 4200.00, "change_24h": 1.8},
            "ADAUSDT": {"price": 0.85, "change_24h": -0.5},
            "SOLUSDT": {"price": 180.00, "change_24h": 3.2},
            "XRPUSDT": {"price": 0.65, "change_24h": -1.2}
        }
        
        if symbol in mock_prices:
            mock_data = mock_prices[symbol]
            return TokenPrice(
                symbol=symbol,
                price=mock_data["price"],
                change_24h=mock_data["change_24h"],
                volume_24h=1000000.0,  # Mock volume
                market_cap=None,
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            raise HTTPException(status_code=404, detail=f"Mock data not available for {symbol}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices/test-sources/{symbol}")
async def test_price_sources(symbol: str):
    """Test all available price sources for a symbol"""
    try:
        import aiohttp
        
        symbol = symbol.upper()
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
        
        results = {}
        
        # Test Binance endpoints
        binance_endpoints = [
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
            f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        ]
        
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(binance_endpoints):
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            results[f"binance_{i+1}"] = {
                                "status": "✅ Available",
                                "price": float(data["price"]),
                                "source": url.split('/')[2]
                            }
                        else:
                            results[f"binance_{i+1}"] = {
                                "status": f"❌ HTTP {response.status}",
                                "source": url.split('/')[2]
                            }
                except Exception as e:
                    results[f"binance_{i+1}"] = {
                        "status": f"❌ {str(e)[:50]}",
                        "source": url.split('/')[2]
                    }
        
        # Test mock data
        mock_available = symbol in ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT"]
        results["mock_data"] = {
            "status": "✅ Available" if mock_available else "❌ Not available",
            "source": "internal_mock"
        }
        
        working_sources = len([r for r in results.values() if "✅" in r["status"]])
        
        return {
            "symbol": symbol,
            "working_sources": working_sources,
            "total_sources": len(results),
            "sources": results,
            "recommendation": "Use mock data" if working_sources == 1 and mock_available else "External APIs available" if working_sources > 1 else "No sources available",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from app.services.crypto_monitor import crypto_monitor
from app.models import (
    TokenPrice, MonitorConfigRequest, MonitorConfigResponse, 
    PriceQueryRequest, MonitorStatusResponse
)
import asyncio

router = APIRouter()

@router.get("/prices", response_model=Dict[str, TokenPrice])
async def get_crypto_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols (e.g., BTC,ETH,ADA)"),
    source: Optional[str] = Query("binance", description="Data source: binance, coingecko, or both"),
    use_cache: Optional[bool] = Query(True, description="Use cached data if available"),
    limit: Optional[int] = Query(None, description="Limit number of results")
):
    """
    Get current prices for crypto tokens
    
    - **symbols**: Optional comma-separated list of symbols
    - **source**: Data source (binance, coingecko, both)
    - **use_cache**: Use cached data for faster response
    - **limit**: Limit number of results
    """
    try:
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        if use_cache and symbol_list:
            cached_prices = crypto_monitor.get_cached_prices(symbol_list)
            if cached_prices:
                if limit:
                    cached_prices = dict(list(cached_prices.items())[:limit])
                return cached_prices
        
        prices = await crypto_monitor.get_all_prices(symbol_list, source)
        crypto_monitor.update_cache(prices)
        
        if limit:
            prices = dict(list(prices.items())[:limit])
        
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices/top/{count}")
async def get_top_crypto_prices(
    count: int = 100,
    source: str = Query("coingecko", description="Data source for market cap ranking")
):
    """Get top N cryptocurrencies by market cap"""
    try:
        if count > 250:
            count = 250
        
        prices = await crypto_monitor.get_all_prices(source=source)
        
        if source == "coingecko":
            sorted_prices = dict(sorted(
                prices.items(), 
                key=lambda x: x[1].market_cap or 0, 
                reverse=True
            )[:count])
        else:
            sorted_prices = dict(list(prices.items())[:count])
        
        return sorted_prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prices/{symbol}")
async def get_single_crypto_price(
    symbol: str,
    source: str = Query("binance", description="Data source")
):
    """Get price for a specific cryptocurrency"""
    try:
        symbol = symbol.upper()
        prices = await crypto_monitor.get_all_prices([symbol], source)
        
        if symbol not in prices:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        return prices[symbol]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/create", response_model=MonitorConfigResponse)
async def create_monitor_config(config: MonitorConfigRequest):
    """
    Create a new monitoring configuration
    
    - **name**: Unique name for the monitor
    - **symbols**: List of crypto symbols to monitor
    - **interval_seconds**: Monitoring interval (default: 60)
    - **price_change_threshold**: Alert threshold for price changes (default: 5%)
    - **volume_change_threshold**: Alert threshold for volume changes (default: 50%)
    - **enabled**: Enable/disable monitoring (default: true)
    - **alert_webhooks**: List of webhook URLs for alerts
    """
    try:
        if config.name in crypto_monitor.monitor_configs:
            raise HTTPException(status_code=400, detail=f"Monitor '{config.name}' already exists")
        
        monitor_config = crypto_monitor.create_monitor_config(
            name=config.name,
            symbols=[s.upper() for s in config.symbols],
            interval_seconds=config.interval_seconds,
            price_change_threshold=config.price_change_threshold,
            volume_change_threshold=config.volume_change_threshold,
            enabled=config.enabled,
            alert_webhooks=config.alert_webhooks
        )
        
        return MonitorConfigResponse(
            name=config.name,
            symbols=monitor_config.symbols,
            interval_seconds=monitor_config.interval_seconds,
            price_change_threshold=monitor_config.price_change_threshold,
            volume_change_threshold=monitor_config.volume_change_threshold,
            enabled=monitor_config.enabled,
            alert_webhooks=monitor_config.alert_webhooks,
            running=False
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/{name}/start")
async def start_monitor(name: str):
    """Start monitoring for a specific configuration"""
    try:
        success = await crypto_monitor.start_monitoring(name)
        if not success:
            raise HTTPException(status_code=404, detail=f"Monitor '{name}' not found or disabled")
        
        return {"message": f"Monitor '{name}' started successfully", "status": "running"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/{name}/stop")
async def stop_monitor(name: str):
    """Stop monitoring for a specific configuration"""
    try:
        success = await crypto_monitor.stop_monitoring(name)
        if not success:
            raise HTTPException(status_code=404, detail=f"Monitor '{name}' not found or not running")
        
        return {"message": f"Monitor '{name}' stopped successfully", "status": "stopped"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor/{name}")
async def get_monitor_config(name: str):
    """Get configuration for a specific monitor"""
    try:
        if name not in crypto_monitor.monitor_configs:
            raise HTTPException(status_code=404, detail=f"Monitor '{name}' not found")
        
        config = crypto_monitor.monitor_configs[name]
        return MonitorConfigResponse(
            name=name,
            symbols=config.symbols,
            interval_seconds=config.interval_seconds,
            price_change_threshold=config.price_change_threshold,
            volume_change_threshold=config.volume_change_threshold,
            enabled=config.enabled,
            alert_webhooks=config.alert_webhooks,
            running=name in crypto_monitor.monitoring_tasks
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/monitor/{name}")
async def update_monitor_config(name: str, config: MonitorConfigRequest):
    """Update an existing monitor configuration"""
    try:
        if name not in crypto_monitor.monitor_configs:
            raise HTTPException(status_code=404, detail=f"Monitor '{name}' not found")
        
        was_running = name in crypto_monitor.monitoring_tasks
        if was_running:
            await crypto_monitor.stop_monitoring(name)
        
        crypto_monitor.create_monitor_config(
            name=name,
            symbols=[s.upper() for s in config.symbols],
            interval_seconds=config.interval_seconds,
            price_change_threshold=config.price_change_threshold,
            volume_change_threshold=config.volume_change_threshold,
            enabled=config.enabled,
            alert_webhooks=config.alert_webhooks
        )
        
        if was_running and config.enabled:
            await crypto_monitor.start_monitoring(name)
        
        updated_config = crypto_monitor.monitor_configs[name]
        return MonitorConfigResponse(
            name=name,
            symbols=updated_config.symbols,
            interval_seconds=updated_config.interval_seconds,
            price_change_threshold=updated_config.price_change_threshold,
            volume_change_threshold=updated_config.volume_change_threshold,
            enabled=updated_config.enabled,
            alert_webhooks=updated_config.alert_webhooks,
            running=name in crypto_monitor.monitoring_tasks
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/monitor/{name}")
async def delete_monitor_config(name: str):
    """Delete a monitor configuration"""
    try:
        if name not in crypto_monitor.monitor_configs:
            raise HTTPException(status_code=404, detail=f"Monitor '{name}' not found")
        
        await crypto_monitor.stop_monitoring(name)
        del crypto_monitor.monitor_configs[name]
        
        return {"message": f"Monitor '{name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor", response_model=MonitorStatusResponse)
async def get_monitor_status():
    """Get status of all monitors"""
    try:
        return crypto_monitor.get_monitor_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitors")
async def list_monitor_configs():
    """List all monitor configurations"""
    try:
        configs = []
        for name, config in crypto_monitor.monitor_configs.items():
            configs.append(MonitorConfigResponse(
                name=name,
                symbols=config.symbols,
                interval_seconds=config.interval_seconds,
                price_change_threshold=config.price_change_threshold,
                volume_change_threshold=config.volume_change_threshold,
                enabled=config.enabled,
                alert_webhooks=config.alert_webhooks,
                running=name in crypto_monitor.monitoring_tasks
            ))
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/start-all")
async def start_all_monitors():
    """Start all enabled monitors"""
    try:
        started = []
        failed = []
        
        for name, config in crypto_monitor.monitor_configs.items():
            if config.enabled:
                success = await crypto_monitor.start_monitoring(name)
                if success:
                    started.append(name)
                else:
                    failed.append(name)
        
        return {
            "message": f"Started {len(started)} monitors",
            "started": started,
            "failed": failed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitor/stop-all")
async def stop_all_monitors():
    """Stop all running monitors"""
    try:
        stopped = []
        
        for name in list(crypto_monitor.monitoring_tasks.keys()):
            success = await crypto_monitor.stop_monitoring(name)
            if success:
                stopped.append(name)
        
        return {
            "message": f"Stopped {len(stopped)} monitors",
            "stopped": stopped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
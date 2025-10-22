import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class TokenPrice:
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    market_cap: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class MonitorConfig:
    symbols: List[str]
    interval_seconds: int = 60
    price_change_threshold: float = 5.0
    volume_change_threshold: float = 50.0
    enabled: bool = True
    alert_webhooks: List[str] = None
    
    def __post_init__(self):
        if self.alert_webhooks is None:
            self.alert_webhooks = []

class CryptoMonitor:
    def __init__(self):
        self.price_cache: Dict[str, TokenPrice] = {}
        self.monitor_configs: Dict[str, MonitorConfig] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_binance_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, TokenPrice]:
        session = await self.get_session()
        
        try:
            if symbols:
                # Convert symbols to USDT pairs and format correctly for Binance API
                usdt_symbols = []
                for s in symbols:
                    if not s.endswith('USDT'):
                        usdt_symbols.append(f'{s}USDT')
                    else:
                        usdt_symbols.append(s)
                
                # Use individual API calls for specific symbols to avoid 400 errors
                prices = {}
                for symbol in usdt_symbols:
                    try:
                        url = f'https://api.binance.com/api/v3/ticker/24hr'
                        params = {'symbol': symbol}
                        
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                item = await response.json()
                                base_symbol = symbol[:-4] if symbol.endswith('USDT') else symbol
                                prices[base_symbol] = TokenPrice(
                                    symbol=base_symbol,
                                    price=float(item['lastPrice']),
                                    change_24h=float(item['priceChangePercent']),
                                    volume_24h=float(item['volume']),
                                    market_cap=None
                                )
                            else:
                                logger.warning(f"Binance API error for {symbol}: {response.status}")
                    except Exception as e:
                        logger.warning(f"Error fetching {symbol} from Binance: {e}")
                        continue
                
                return prices
            else:
                # Get all symbols
                url = 'https://api.binance.com/api/v3/ticker/24hr'
                params = {}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if not isinstance(data, list):
                            data = [data]
                        
                        prices = {}
                        for item in data:
                            symbol = item['symbol']
                            if symbol.endswith('USDT'):
                                base_symbol = symbol[:-4]
                                prices[base_symbol] = TokenPrice(
                                    symbol=base_symbol,
                                    price=float(item['lastPrice']),
                                    change_24h=float(item['priceChangePercent']),
                                    volume_24h=float(item['volume']),
                                    market_cap=None
                                )
                        return prices
                    else:
                        logger.error(f"Binance API error: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching Binance prices: {e}")
            return {}
    
    async def fetch_coingecko_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, TokenPrice]:
        session = await self.get_session()
        
        # Symbol to CoinGecko ID mapping for common tokens
        symbol_to_id = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'ADA': 'cardano',
            'SOL': 'solana',
            'XRP': 'ripple',
            'DOGE': 'dogecoin',
            'MATIC': 'matic-network',
            'DOT': 'polkadot',
            'AVAX': 'avalanche-2',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'MKR': 'maker',
            'SNX': 'havven',
            'CRV': 'curve-dao-token'
        }
        
        try:
            if symbols:
                # Convert symbols to CoinGecko IDs
                coin_ids = []
                for symbol in symbols:
                    symbol_upper = symbol.upper()
                    if symbol_upper in symbol_to_id:
                        coin_ids.append(symbol_to_id[symbol_upper])
                    else:
                        coin_ids.append(symbol.lower())
                
                ids = ','.join(coin_ids)
                url = f'https://api.coingecko.com/api/v3/simple/price'
                params = {
                    'ids': ids,
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true',
                    'include_24hr_vol': 'true',
                    'include_market_cap': 'true'
                }
            else:
                url = 'https://api.coingecko.com/api/v3/coins/markets'
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 250,
                    'page': 1
                }
            
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {}
                    
                    if 'coins/markets' in url:
                        for coin in data:
                            prices[coin['symbol'].upper()] = TokenPrice(
                                symbol=coin['symbol'].upper(),
                                price=float(coin['current_price'] or 0),
                                change_24h=float(coin['price_change_percentage_24h'] or 0),
                                volume_24h=float(coin['total_volume'] or 0),
                                market_cap=float(coin['market_cap'] or 0)
                            )
                    else:
                        # Map CoinGecko IDs back to symbols
                        id_to_symbol = {v: k for k, v in symbol_to_id.items()}
                        
                        for coin_id, coin_data in data.items():
                            symbol = id_to_symbol.get(coin_id, coin_id).upper()
                            prices[symbol] = TokenPrice(
                                symbol=symbol,
                                price=float(coin_data.get('usd', 0)),
                                change_24h=float(coin_data.get('usd_24h_change', 0)),
                                volume_24h=float(coin_data.get('usd_24h_vol', 0)),
                                market_cap=float(coin_data.get('usd_market_cap', 0))
                            )
                    return prices
                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching CoinGecko prices: {e}")
            return {}
    
    async def get_all_prices(self, symbols: Optional[List[str]] = None, source: str = 'binance') -> Dict[str, TokenPrice]:
        if source == 'binance':
            return await self.fetch_binance_prices(symbols)
        elif source == 'coingecko':
            return await self.fetch_coingecko_prices(symbols)
        else:
            binance_prices = await self.fetch_binance_prices(symbols)
            coingecko_prices = await self.fetch_coingecko_prices(symbols)
            binance_prices.update(coingecko_prices)
            return binance_prices
    
    def update_cache(self, prices: Dict[str, TokenPrice]):
        for symbol, price_data in prices.items():
            self.price_cache[symbol] = price_data
    
    def get_cached_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, TokenPrice]:
        if symbols:
            return {s: self.price_cache[s] for s in symbols if s in self.price_cache}
        return self.price_cache.copy()
    
    def create_monitor_config(self, 
                            name: str,
                            symbols: List[str],
                            interval_seconds: int = 60,
                            price_change_threshold: float = 5.0,
                            volume_change_threshold: float = 50.0,
                            enabled: bool = True,
                            alert_webhooks: Optional[List[str]] = None) -> MonitorConfig:
        config = MonitorConfig(
            symbols=symbols,
            interval_seconds=interval_seconds,
            price_change_threshold=price_change_threshold,
            volume_change_threshold=volume_change_threshold,
            enabled=enabled,
            alert_webhooks=alert_webhooks or []
        )
        self.monitor_configs[name] = config
        return config
    
    async def start_monitoring(self, config_name: str) -> bool:
        if config_name not in self.monitor_configs:
            return False
        
        config = self.monitor_configs[config_name]
        if not config.enabled:
            return False
        
        if config_name in self.monitoring_tasks:
            self.monitoring_tasks[config_name].cancel()
        
        task = asyncio.create_task(self._monitor_loop(config_name, config))
        self.monitoring_tasks[config_name] = task
        return True
    
    async def stop_monitoring(self, config_name: str) -> bool:
        if config_name in self.monitoring_tasks:
            self.monitoring_tasks[config_name].cancel()
            del self.monitoring_tasks[config_name]
            return True
        return False
    
    async def _monitor_loop(self, config_name: str, config: MonitorConfig):
        logger.info(f"Starting monitoring for {config_name} with {len(config.symbols)} symbols: {config.symbols}")
        
        while True:
            try:
                logger.debug(f"Fetching prices for {config_name}: {config.symbols}")
                prices = await self.get_all_prices(config.symbols, source='binance')
                
                if prices:
                    logger.debug(f"Successfully fetched {len(prices)} prices for {config_name}")
                    self.update_cache(prices)
                    await self._check_alerts(config_name, config, prices)
                else:
                    logger.warning(f"No prices fetched for {config_name}, trying CoinGecko as fallback")
                    # Try CoinGecko as fallback
                    prices = await self.get_all_prices(config.symbols, source='coingecko')
                    if prices:
                        logger.info(f"Fallback successful: fetched {len(prices)} prices from CoinGecko")
                        self.update_cache(prices)
                        await self._check_alerts(config_name, config, prices)
                    else:
                        logger.error(f"Failed to fetch prices from both sources for {config_name}")
                
                await asyncio.sleep(config.interval_seconds)
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring stopped for {config_name}")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for {config_name}: {e}")
                await asyncio.sleep(config.interval_seconds)
    
    async def _check_alerts(self, config_name: str, config: MonitorConfig, current_prices: Dict[str, TokenPrice]):
        alerts = []
        
        for symbol in config.symbols:
            if symbol not in current_prices:
                continue
                
            current = current_prices[symbol]
            
            if abs(current.change_24h) >= config.price_change_threshold:
                alerts.append({
                    'type': 'price_change',
                    'symbol': symbol,
                    'change_24h': current.change_24h,
                    'threshold': config.price_change_threshold,
                    'current_price': current.price,
                    'timestamp': current.timestamp
                })
        
        if alerts:
            logger.info(f"Generated {len(alerts)} alerts for {config_name}")
            await self._send_alerts(config, alerts)
    
    async def _send_alerts(self, config: MonitorConfig, alerts: List[Dict]):
        if not config.alert_webhooks:
            return
        
        session = await self.get_session()
        
        for webhook_url in config.alert_webhooks:
            try:
                payload = {
                    'alerts': alerts,
                    'timestamp': datetime.now().isoformat()
                }
                async with session.post(webhook_url, json=payload, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Webhook alert failed: {response.status}")
            except Exception as e:
                logger.error(f"Error sending webhook alert: {e}")
    
    def get_monitor_status(self) -> Dict[str, Any]:
        return {
            'active_monitors': len(self.monitoring_tasks),
            'cached_tokens': len(self.price_cache),
            'monitor_configs': {
                name: {
                    'symbols_count': len(config.symbols),
                    'interval_seconds': config.interval_seconds,
                    'enabled': config.enabled,
                    'running': name in self.monitoring_tasks
                }
                for name, config in self.monitor_configs.items()
            }
        }

crypto_monitor = CryptoMonitor()
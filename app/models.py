from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class MarketAlert(BaseModel):
    symbol: str
    crash_probability: float
    indicators: List[str]
    timestamp: datetime
    asi_analysis: Optional[str] = None

class AgentStatus(BaseModel):
    agent_running: bool
    latest_alerts: List[str]
    message: str

class TokenPrice(BaseModel):
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    market_cap: Optional[float] = None
    timestamp: str

class MonitorConfigRequest(BaseModel):
    name: str
    symbols: List[str]
    interval_seconds: Optional[int] = 60
    price_change_threshold: Optional[float] = 5.0
    volume_change_threshold: Optional[float] = 50.0
    enabled: Optional[bool] = True
    alert_webhooks: Optional[List[str]] = []

class MonitorConfigResponse(BaseModel):
    name: str
    symbols: List[str]
    interval_seconds: int
    price_change_threshold: float
    volume_change_threshold: float
    enabled: bool
    alert_webhooks: List[str]
    running: bool

class PriceQueryRequest(BaseModel):
    symbols: Optional[List[str]] = None
    source: Optional[str] = "binance"
    use_cache: Optional[bool] = True

class MonitorStatusResponse(BaseModel):
    active_monitors: int
    cached_tokens: int
    monitor_configs: Dict[str, Any]
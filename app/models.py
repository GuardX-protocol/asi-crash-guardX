from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import Document
from pymongo import IndexModel

class User(Document):
    walletAddress: str = Field(..., unique=True, description="Unique wallet address or Telegram-based ID")
    email: Optional[str] = Field(None, description="User email address")
    telegramId: Optional[str] = Field(None, description="Telegram user ID for bot integration")
    username: Optional[str] = Field(None, description="Telegram username")
    firstName: Optional[str] = Field(None, description="User's first name")
    lastName: Optional[str] = Field(None, description="User's last name")
    languageCode: Optional[str] = Field("en", description="User's preferred language code")
    isActive: bool = Field(True, description="Whether the user account is active")
    notificationPreferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "telegram_alerts": True,
            "email_alerts": False,
            "webhook_alerts": False
        },
        description="User notification preferences"
    )
    monitors: List[str] = Field(default_factory=list, description="List of monitor IDs associated with user")
    createdAt: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updatedAt: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    lastLoginAt: Optional[datetime] = Field(None, description="Last login/interaction timestamp")
    
    class Settings:
        name = "users"
        indexes = [
            IndexModel("walletAddress", unique=True),
            IndexModel("email"),
            IndexModel("telegramId", unique=True, sparse=True),
            IndexModel("username"),
            IndexModel([("firstName", 1), ("lastName", 1)])
        ]

class Monitor(Document):
    name: str = Field(..., unique=True)
    userId: str
    symbols: List[str]
    interval_seconds: int = 300
    interval_str: str = "5m"
    price_change_threshold: float = 5.0
    volume_change_threshold: float = 50.0
    crash_probability_threshold: float = 60.0
    enabled: bool = True
    alert_webhooks: List[str] = Field(default_factory=list)
    telegram_alerts: bool = False
    email_alerts: bool = False
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "monitors"
        indexes = [
            IndexModel("name", unique=True),
            IndexModel("userId"),
            IndexModel("enabled")
        ]

class MonitorAlert(Document):
    monitorId: str
    userId: str
    symbol: str
    alertType: str
    crash_probability: Optional[float] = None
    price_change: Optional[float] = None
    volume_change: Optional[float] = None
    current_price: float
    asi_analysis: Optional[str] = None
    technical_indicators: Dict[str, Any] = Field(default_factory=dict)
    severity: str
    sent_telegram: bool = False
    sent_email: bool = False
    sent_webhook: bool = False
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "monitor_alerts"
        indexes = [
            IndexModel("monitorId"),
            IndexModel("userId"),
            IndexModel("symbol"),
            IndexModel("createdAt"),
            IndexModel("severity")
        ]

class UserCreate(BaseModel):
    walletAddress: str
    email: Optional[str] = None
    telegramId: Optional[str] = None
    username: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    languageCode: Optional[str] = "en"
    notificationPreferences: Optional[Dict[str, bool]] = None

class Item(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    owner_id: int

class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    owner_id: int

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
    userId: str
    symbols: List[str]
    interval_seconds: Optional[int] = None
    interval_str: Optional[str] = "5m"
    price_change_threshold: Optional[float] = 5.0
    volume_change_threshold: Optional[float] = 50.0
    crash_probability_threshold: Optional[float] = 60.0
    enabled: Optional[bool] = True
    alert_webhooks: Optional[List[str]] = []
    telegram_alerts: Optional[bool] = False
    email_alerts: Optional[bool] = False

class MonitorConfigResponse(BaseModel):
    name: str
    userId: str
    symbols: List[str]
    interval_seconds: int
    interval_str: str
    price_change_threshold: float
    volume_change_threshold: float
    crash_probability_threshold: float
    enabled: bool
    alert_webhooks: List[str]
    telegram_alerts: bool
    email_alerts: bool
    running: bool

class PriceQueryRequest(BaseModel):
    symbols: Optional[List[str]] = None
    source: Optional[str] = "binance"
    use_cache: Optional[bool] = True

class MonitorStatusResponse(BaseModel):
    active_monitors: int
    cached_tokens: int
    monitor_configs: Dict[str, Any]
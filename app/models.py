from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import Document, PydanticObjectId
from pymongo import IndexModel

class MonitorReference(BaseModel):
    """Reference to a monitor with ID and name for easy access"""
    id: str = Field(..., description="Monitor ID")
    name: str = Field(..., description="Monitor name")
    enabled: bool = Field(True, description="Whether the monitor is enabled")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When this monitor was created")
    symbols: List[str] = Field(default_factory=list, description="Symbols being monitored")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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
    monitors: List[MonitorReference] = Field(default_factory=list, description="List of monitors associated with user")
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
    userId: str = Field(..., description="User wallet address who created this monitor")
    symbols: List[str]
    crash_threshold: float = Field(default=10.0, description="Minimum price drop % to trigger alert")
    enabled: bool = True
    notification_channels: List[str] = Field(default_factory=lambda: ["telegram"], description="telegram, email")
    interval_seconds: int = 300
    interval_str: str = "5m"
    price_change_threshold: float = 5.0
    volume_change_threshold: float = 50.0
    crash_probability_threshold: float = 60.0
    alert_webhooks: List[str] = Field(default_factory=list)
    telegram_alerts: bool = False
    email_alerts: bool = False
    last_check: Optional[datetime] = Field(None, description="Last time this monitor was checked")
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
    monitorId: str = Field(..., description="Monitor ID that triggered this alert")
    userId: str = Field(..., description="User wallet address who owns the monitor")
    symbol: str = Field(..., description="The cryptocurrency symbol that crashed (e.g., BTCUSDT)")
    token_name: str = Field(..., description="Human readable token name (e.g., Bitcoin)")
    crash_probability: Optional[float] = None
    current_price: float
    price_drop: float = Field(description="Price drop percentage")
    price_before_crash: Optional[float] = Field(None, description="Price before the crash")
    analysis: str = Field(description="AI analysis of the crash")
    crash_detected_at: datetime = Field(default_factory=datetime.utcnow, description="When the crash was detected")
    notification_sent: bool = False
    notification_channels: List[str] = Field(default_factory=list, description="Channels where notification was sent")
    telegram_sent: bool = False
    email_sent: bool = False
    webhook_sent: bool = False
    # Technical analysis data
    technical_indicators: Dict[str, Any] = Field(default_factory=dict, description="Technical analysis indicators")
    asi_analysis: Optional[str] = None
    confidence_level: Optional[str] = Field(None, description="Confidence level of crash detection")
    # Legacy fields for backward compatibility
    alertType: Optional[str] = None
    price_change: Optional[float] = None
    volume_change: Optional[float] = None
    severity: Optional[str] = None
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
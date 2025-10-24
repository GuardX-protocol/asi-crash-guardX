from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from dataclasses import dataclass, asdict

@dataclass
class InMemoryUser:
    walletAddress: str
    email: Optional[str] = None
    telegramId: Optional[str] = None
    username: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    languageCode: Optional[str] = "en"
    isActive: bool = True
    notificationPreferences: Dict[str, Any] = None
    monitors: List[str] = None
    createdAt: datetime = None
    updatedAt: datetime = None
    lastLoginAt: Optional[datetime] = None
    
    def __post_init__(self):
        if self.monitors is None:
            self.monitors = []
        if self.notificationPreferences is None:
            self.notificationPreferences = {
                "telegram_alerts": True,
                "email_alerts": False,
                "webhook_alerts": False
            }
        if self.createdAt is None:
            self.createdAt = datetime.utcnow()
        if self.updatedAt is None:
            self.updatedAt = datetime.utcnow()

@dataclass
class InMemoryMonitor:
    name: str
    userId: str
    symbols: List[str]
    interval_seconds: int = 300
    interval_str: str = "5m"
    price_change_threshold: float = 5.0
    volume_change_threshold: float = 50.0
    crash_probability_threshold: float = 60.0
    enabled: bool = True
    alert_webhooks: List[str] = None
    telegram_alerts: bool = False
    email_alerts: bool = False
    createdAt: datetime = None
    updatedAt: datetime = None
    
    def __post_init__(self):
        if self.alert_webhooks is None:
            self.alert_webhooks = []
        if self.createdAt is None:
            self.createdAt = datetime.utcnow()
        if self.updatedAt is None:
            self.updatedAt = datetime.utcnow()

@dataclass
class InMemoryAlert:
    monitorId: str
    userId: str
    symbol: str
    alertType: str
    crash_probability: Optional[float] = None
    price_change: Optional[float] = None
    volume_change: Optional[float] = None
    current_price: float = 0.0
    asi_analysis: Optional[str] = None
    technical_indicators: Dict[str, Any] = None
    severity: str = "MEDIUM"
    sent_telegram: bool = False
    sent_email: bool = False
    sent_webhook: bool = False
    createdAt: datetime = None
    
    def __post_init__(self):
        if self.technical_indicators is None:
            self.technical_indicators = {}
        if self.createdAt is None:
            self.createdAt = datetime.utcnow()

class FallbackStorage:
    def __init__(self):
        self.users: Dict[str, InMemoryUser] = {}
        self.monitors: Dict[str, InMemoryMonitor] = {}
        self.alerts: List[InMemoryAlert] = []
    
    # User operations
    async def create_user(self, user_data: dict) -> InMemoryUser:
        user = InMemoryUser(**user_data)
        self.users[user.walletAddress] = user
        return user
    
    async def get_user(self, wallet_address: str) -> Optional[InMemoryUser]:
        return self.users.get(wallet_address)
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[InMemoryUser]:
        users_list = list(self.users.values())
        return users_list[skip:skip + limit]
    
    async def update_user(self, wallet_address: str, update_data: dict) -> Optional[InMemoryUser]:
        if wallet_address in self.users:
            user = self.users[wallet_address]
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updatedAt = datetime.utcnow()
            return user
        return None
    
    async def delete_user(self, wallet_address: str) -> bool:
        if wallet_address in self.users:
            del self.users[wallet_address]
            return True
        return False
    
    # Monitor operations
    async def create_monitor(self, monitor_data: dict) -> InMemoryMonitor:
        monitor = InMemoryMonitor(**monitor_data)
        self.monitors[monitor.name] = monitor
        return monitor
    
    async def get_monitor(self, name: str) -> Optional[InMemoryMonitor]:
        return self.monitors.get(name)
    
    async def get_monitors(self, user_id: Optional[str] = None) -> List[InMemoryMonitor]:
        monitors_list = list(self.monitors.values())
        if user_id:
            monitors_list = [m for m in monitors_list if m.userId == user_id]
        return monitors_list
    
    async def update_monitor(self, name: str, update_data: dict) -> Optional[InMemoryMonitor]:
        if name in self.monitors:
            monitor = self.monitors[name]
            for key, value in update_data.items():
                if hasattr(monitor, key):
                    setattr(monitor, key, value)
            monitor.updatedAt = datetime.utcnow()
            return monitor
        return None
    
    async def delete_monitor(self, name: str) -> bool:
        if name in self.monitors:
            del self.monitors[name]
            return True
        return False
    
    # Alert operations
    async def create_alert(self, alert_data: dict) -> InMemoryAlert:
        alert = InMemoryAlert(**alert_data)
        self.alerts.append(alert)
        # Keep only last 1000 alerts to prevent memory issues
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        return alert
    
    async def get_alerts(self, user_id: Optional[str] = None, symbol: Optional[str] = None, 
                        severity: Optional[str] = None, limit: int = 100) -> List[InMemoryAlert]:
        filtered_alerts = self.alerts
        
        if user_id:
            filtered_alerts = [a for a in filtered_alerts if a.userId == user_id]
        if symbol:
            filtered_alerts = [a for a in filtered_alerts if a.symbol == symbol.upper()]
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        # Sort by creation time (newest first)
        filtered_alerts.sort(key=lambda x: x.createdAt, reverse=True)
        return filtered_alerts[:limit]

fallback_storage = FallbackStorage()
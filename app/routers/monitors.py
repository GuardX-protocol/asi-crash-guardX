"""
Monitor management router with CRUD operations
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.models import Monitor, User, MonitorAlert
from app.database import ensure_connection
from app.services.email_service import email_service
from app.routers.telegram_webhook import send_telegram_message_direct

logger = logging.getLogger(__name__)

router = APIRouter()

class MonitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    symbols: List[str] = Field(..., min_items=1, max_items=20)
    crash_threshold: float = Field(default=10.0, ge=1.0, le=50.0)
    enabled: bool = Field(default=True)
    notification_channels: List[str] = Field(default=["telegram"], description="telegram, email")

class MonitorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbols: Optional[List[str]] = Field(None, min_items=1, max_items=20)
    crash_threshold: Optional[float] = Field(None, ge=1.0, le=50.0)
    enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None

class MonitorResponse(BaseModel):
    id: str
    name: str
    symbols: List[str]
    crash_threshold: float
    enabled: bool
    notification_channels: List[str]
    userId: str
    createdAt: datetime
    updatedAt: datetime
    last_check: Optional[datetime] = None
    alerts_count: int = 0

@router.post("/", response_model=MonitorResponse)
async def create_monitor(
    monitor_data: MonitorCreate,
    user_id: str,
    background_tasks: BackgroundTasks
):
    """Create a new monitor"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Validate user exists by wallet address or user ID
        user = None
        
        # First try to find by wallet address (if it looks like one)
        if user_id.startswith('0x') or len(user_id) > 20:
            user = await User.find_one(User.walletAddress == user_id)
        
        # If not found, try by ObjectId
        if not user:
            try:
                from bson import ObjectId
                user_object_id = ObjectId(user_id)
                user = await User.get(user_object_id)
            except:
                pass
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use wallet address as the userId for the monitor
        wallet_address = user.walletAddress
        
        # Validate symbols format
        validated_symbols = []
        for symbol in monitor_data.symbols:
            symbol = symbol.upper().strip()
            if not symbol.endswith('USDT'):
                symbol += 'USDT'
            validated_symbols.append(symbol)
        
        # Create monitor
        monitor = Monitor(
            name=monitor_data.name,
            symbols=validated_symbols,
            crash_threshold=monitor_data.crash_threshold,
            enabled=monitor_data.enabled,
            notification_channels=monitor_data.notification_channels,
            userId=wallet_address,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        await monitor.insert()
        
        # Add monitor reference to user's monitors array
        from app.models import MonitorReference
        monitor_ref = MonitorReference(
            id=str(monitor.id),
            name=monitor.name,
            enabled=monitor.enabled,
            created_at=monitor.createdAt,
            symbols=monitor.symbols
        )
        
        # Update user's monitors array
        if not user.monitors:
            user.monitors = []
        user.monitors.append(monitor_ref)
        user.updatedAt = datetime.utcnow()
        await user.save()
        
        # Send notifications in background
        background_tasks.add_task(
            send_monitor_created_notifications,
            user,
            monitor
        )
        
        # Start monitoring this new monitor
        background_tasks.add_task(start_monitoring_symbols, validated_symbols)
        
        logger.info(f"Monitor created: {monitor.name} for user {user_id}")
        
        return MonitorResponse(
            id=str(monitor.id),
            name=monitor.name,
            symbols=monitor.symbols,
            crash_threshold=monitor.crash_threshold,
            enabled=monitor.enabled,
            notification_channels=monitor.notification_channels,
            userId=monitor.userId,
            createdAt=monitor.createdAt,
            updatedAt=monitor.updatedAt,
            alerts_count=0
        )
        
    except Exception as e:
        logger.error(f"Error creating monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[MonitorResponse])
async def get_user_monitors(user_id: str):
    """Get all monitors for a user"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Find user to get wallet address
        user = None
        
        # First try to find by wallet address (if it looks like one)
        if user_id.startswith('0x') or len(user_id) > 20:
            user = await User.find_one(User.walletAddress == user_id)
            wallet_address = user_id
        else:
            # Try by ObjectId
            try:
                from bson import ObjectId
                user_object_id = ObjectId(user_id)
                user = await User.get(user_object_id)
                wallet_address = user.walletAddress if user else None
            except:
                raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        if not user or not wallet_address:
            raise HTTPException(status_code=404, detail="User not found")
            
        monitors = await Monitor.find(Monitor.userId == wallet_address).to_list()
        
        # Get alert counts for each monitor
        monitor_responses = []
        for monitor in monitors:
            alerts_count = await MonitorAlert.find(
                MonitorAlert.monitorId == str(monitor.id)
            ).count()
            
            monitor_responses.append(MonitorResponse(
                id=str(monitor.id),
                name=monitor.name,
                symbols=monitor.symbols,
                crash_threshold=monitor.crash_threshold,
                enabled=monitor.enabled,
                notification_channels=monitor.notification_channels,
                userId=monitor.userId,
                createdAt=monitor.createdAt,
                updatedAt=monitor.updatedAt,
                last_check=getattr(monitor, 'last_check', None),
                alerts_count=alerts_count
            ))
        
        return monitor_responses
        
    except Exception as e:
        logger.error(f"Error getting monitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: str, user_id: str):
    """Get a specific monitor"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Convert monitor_id to ObjectId
        from bson import ObjectId
        try:
            monitor_object_id = ObjectId(monitor_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid monitor ID format")
        
        monitor = await Monitor.get(monitor_object_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        # Find user to get wallet address
        user = None
        if user_id.startswith('0x') or len(user_id) > 20:
            user = await User.find_one(User.walletAddress == user_id)
            wallet_address = user_id
        else:
            try:
                user_object_id = ObjectId(user_id)
                user = await User.get(user_object_id)
                wallet_address = user.walletAddress if user else None
            except:
                raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        if not user or not wallet_address:
            raise HTTPException(status_code=404, detail="User not found")
        
        if monitor.userId != wallet_address:
            raise HTTPException(status_code=403, detail="Access denied")
        
        alerts_count = await MonitorAlert.find(
            MonitorAlert.monitorId == str(monitor_object_id)
        ).count()
        
        return MonitorResponse(
            id=str(monitor.id),
            name=monitor.name,
            symbols=monitor.symbols,
            crash_threshold=monitor.crash_threshold,
            enabled=monitor.enabled,
            notification_channels=monitor.notification_channels,
            userId=monitor.userId,
            createdAt=monitor.createdAt,
            updatedAt=monitor.updatedAt,
            last_check=getattr(monitor, 'last_check', None),
            alerts_count=alerts_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: str,
    user_id: str,
    monitor_update: MonitorUpdate,
    background_tasks: BackgroundTasks
):
    """Update a monitor (PATCH operation)"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        monitor = await Monitor.get(monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        if monitor.userId != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update only provided fields
        update_data = monitor_update.dict(exclude_unset=True)
        
        if "symbols" in update_data:
            # Validate and format symbols
            validated_symbols = []
            for symbol in update_data["symbols"]:
                symbol = symbol.upper().strip()
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                validated_symbols.append(symbol)
            update_data["symbols"] = validated_symbols
        
        # Update fields
        for field, value in update_data.items():
            setattr(monitor, field, value)
        
        monitor.updatedAt = datetime.utcnow()
        await monitor.save()
        
        # Update monitor reference in user's monitors array
        user = await User.find_one(User.walletAddress == monitor.userId)
        if user and user.monitors:
            for i, monitor_ref in enumerate(user.monitors):
                if monitor_ref.id == monitor_id:
                    # Update the monitor reference
                    user.monitors[i].name = monitor.name
                    user.monitors[i].enabled = monitor.enabled
                    user.monitors[i].symbols = monitor.symbols
                    break
            user.updatedAt = datetime.utcnow()
            await user.save()
        
        # If symbols changed, update monitoring
        if "symbols" in update_data:
            background_tasks.add_task(start_monitoring_symbols, update_data["symbols"])
        
        alerts_count = await MonitorAlert.find(
            MonitorAlert.monitorId == monitor_id
        ).count()
        
        logger.info(f"Monitor updated: {monitor.name} for user {user_id}")
        
        return MonitorResponse(
            id=str(monitor.id),
            name=monitor.name,
            symbols=monitor.symbols,
            crash_threshold=monitor.crash_threshold,
            enabled=monitor.enabled,
            notification_channels=monitor.notification_channels,
            userId=monitor.userId,
            createdAt=monitor.createdAt,
            updatedAt=monitor.updatedAt,
            last_check=getattr(monitor, 'last_check', None),
            alerts_count=alerts_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{monitor_id}")
async def delete_monitor(monitor_id: str, user_id: str):
    """Delete a monitor"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        monitor = await Monitor.get(monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        if monitor.userId != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete associated alerts
        alerts = await MonitorAlert.find(MonitorAlert.monitorId == monitor_id).to_list()
        for alert in alerts:
            await alert.delete()
        
        # Remove monitor reference from user's monitors array
        user = await User.find_one(User.walletAddress == monitor.userId)
        if user and user.monitors:
            user.monitors = [m for m in user.monitors if m.id != monitor_id]
            user.updatedAt = datetime.utcnow()
            await user.save()
        
        # Delete monitor
        await monitor.delete()
        
        logger.info(f"Monitor deleted: {monitor.name} for user {user_id}")
        
        return {"message": "Monitor deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{monitor_id}/toggle")
async def toggle_monitor(monitor_id: str, user_id: str):
    """Toggle monitor enabled/disabled status"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        monitor = await Monitor.get(monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        if monitor.userId != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        monitor.enabled = not monitor.enabled
        monitor.updatedAt = datetime.utcnow()
        await monitor.save()
        
        # Update monitor reference in user's monitors array
        user = await User.find_one(User.walletAddress == monitor.userId)
        if user and user.monitors:
            for monitor_ref in user.monitors:
                if monitor_ref.id == monitor_id:
                    monitor_ref.enabled = monitor.enabled
                    break
            user.updatedAt = datetime.utcnow()
            await user.save()
        
        status = "enabled" if monitor.enabled else "disabled"
        logger.info(f"Monitor {status}: {monitor.name} for user {user_id}")
        
        return {
            "message": f"Monitor {status} successfully",
            "enabled": monitor.enabled
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{monitor_id}/alerts")
async def get_monitor_alerts(
    monitor_id: str,
    user_id: str,
    limit: int = 50,
    skip: int = 0
):
    """Get alerts for a specific monitor"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Verify monitor ownership
        monitor = await Monitor.get(monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        if monitor.userId != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get alerts
        alerts = await MonitorAlert.find(
            MonitorAlert.monitorId == monitor_id
        ).sort(-MonitorAlert.createdAt).skip(skip).limit(limit).to_list()
        
        return {
            "monitor_id": monitor_id,
            "monitor_name": monitor.name,
            "alerts": [
                {
                    "id": str(alert.id),
                    "symbol": alert.symbol,
                    "crash_probability": alert.crash_probability,
                    "current_price": alert.current_price,
                    "price_drop": alert.price_drop,
                    "analysis": alert.analysis,
                    "createdAt": alert.createdAt,
                    "notification_sent": alert.notification_sent
                }
                for alert in alerts
            ],
            "total_alerts": len(alerts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monitor alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def send_monitor_created_notifications(user: User, monitor: Monitor):
    """Send notifications when a monitor is created"""
    try:
        # Send Telegram notification
        if user.telegramId and "telegram" in monitor.notification_channels:
            message = f"""
🎯 *Monitor Created Successfully!*

📊 *Name:* {monitor.name}
💰 *Symbols:* {', '.join(monitor.symbols)}
⚠️ *Crash Threshold:* {monitor.crash_threshold}%
🔔 *Notifications:* {', '.join(monitor.notification_channels)}

Your monitor is now active and will alert you when crash conditions are detected!

Use /monitors to manage your monitors.
            """
            await send_telegram_message_direct(str(user.telegramId), message)
        
        # Send email notification
        if (user.email and 
            user.notificationPreferences.get("email_alerts", False) and 
            "email" in monitor.notification_channels):
            await email_service.send_monitor_created_notification(
                user.email,
                monitor.name,
                monitor.symbols,
                user.firstName or user.username
            )
        
        logger.info(f"Monitor creation notifications sent for {monitor.name}")
        
    except Exception as e:
        logger.error(f"Error sending monitor created notifications: {e}")

async def start_monitoring_symbols(symbols: List[str]):
    """Start monitoring new symbols (placeholder for background service)"""
    try:
        # This would typically trigger the monitoring service to add these symbols
        # For now, we'll just log it
        logger.info(f"Started monitoring symbols: {', '.join(symbols)}")
        
        # In a real implementation, this would:
        # 1. Add symbols to the active monitoring list
        # 2. Start price data collection
        # 3. Initialize crash detection for these symbols
        
    except Exception as e:
        logger.error(f"Error starting symbol monitoring: {e}")

@router.get("/stats/summary")
async def get_monitoring_stats(user_id: str):
    """Get monitoring statistics for a user"""
    try:
        if not await ensure_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Get user monitors
        monitors = await Monitor.find(Monitor.userId == user_id).to_list()
        
        # Calculate stats
        total_monitors = len(monitors)
        active_monitors = len([m for m in monitors if m.enabled])
        total_symbols = len(set(symbol for monitor in monitors for symbol in monitor.symbols))
        
        # Get recent alerts (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_alerts = 0
        for monitor in monitors:
            alerts_count = await MonitorAlert.find(
                MonitorAlert.monitorId == str(monitor.id),
                MonitorAlert.createdAt >= week_ago
            ).count()
            recent_alerts += alerts_count
        
        return {
            "total_monitors": total_monitors,
            "active_monitors": active_monitors,
            "inactive_monitors": total_monitors - active_monitors,
            "total_symbols": total_symbols,
            "recent_alerts_7d": recent_alerts,
            "monitors": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "symbols_count": len(m.symbols),
                    "enabled": m.enabled,
                    "last_updated": m.updatedAt
                }
                for m in monitors
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
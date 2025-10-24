from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.models import User, UserCreate
from app.database import is_connected
from app.services.fallback_storage import fallback_storage
from datetime import datetime

router = APIRouter()

@router.post("/")
async def create_user(user: UserCreate):
    if is_connected():
        existing_user = await User.find_one(User.walletAddress == user.walletAddress)
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this wallet address already exists")
        
        new_user = User(**user.dict())
        await new_user.insert()
        return new_user
    else:
        existing_user = await fallback_storage.get_user(user.walletAddress)
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this wallet address already exists")
        
        new_user = await fallback_storage.create_user(user.dict())
        return new_user

@router.get("/{wallet_address}")
async def get_user(wallet_address: str):
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    else:
        user = await fallback_storage.get_user(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@router.get("/")
async def get_users(skip: int = 0, limit: int = 100):
    if is_connected():
        users = await User.find_all().skip(skip).limit(limit).to_list()
        return users
    else:
        users = await fallback_storage.get_users(skip, limit)
        return users

@router.put("/{wallet_address}")
async def update_user(wallet_address: str, user_update: dict):
    """Full update of user (replaces all fields)"""
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_update["updatedAt"] = datetime.utcnow()
        await user.update({"$set": user_update})
        return await User.find_one(User.walletAddress == wallet_address)
    else:
        user_update["updatedAt"] = datetime.utcnow()
        user = await fallback_storage.update_user(wallet_address, user_update)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@router.patch("/{wallet_address}")
async def patch_user(wallet_address: str, user_patch: dict):
    """Partial update of user (updates only provided fields)"""
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Only update provided fields
        update_fields = {k: v for k, v in user_patch.items() if v is not None}
        update_fields["updatedAt"] = datetime.utcnow()
        
        await user.update({"$set": update_fields})
        return await User.find_one(User.walletAddress == wallet_address)
    else:
        # Only update provided fields
        update_fields = {k: v for k, v in user_patch.items() if v is not None}
        update_fields["updatedAt"] = datetime.utcnow()
        
        user = await fallback_storage.update_user(wallet_address, update_fields)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@router.delete("/{wallet_address}")
async def delete_user(wallet_address: str):
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        await user.delete()
        return {"message": "User deleted successfully"}
    else:
        success = await fallback_storage.delete_user(wallet_address)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}

@router.get("/{wallet_address}/profile")
async def get_user_profile(wallet_address: str):
    """Get detailed user profile with statistics"""
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's monitors and alerts
        from app.models import Monitor, MonitorAlert
        monitors = await Monitor.find(Monitor.userId == wallet_address).to_list()
        alerts = await MonitorAlert.find(MonitorAlert.userId == wallet_address).to_list()
        
        profile = {
            "user": user,
            "statistics": {
                "total_monitors": len(monitors),
                "active_monitors": len([m for m in monitors if m.enabled]),
                "total_alerts": len(alerts),
                "recent_alerts": len([a for a in alerts if (datetime.utcnow() - a.createdAt).days <= 7])
            },
            "preferences": user.notificationPreferences,
            "account_age_days": (datetime.utcnow() - user.createdAt).days if user.createdAt else 0
        }
        
        return profile
    else:
        user = await fallback_storage.get_user(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        monitors = await fallback_storage.get_monitors(wallet_address)
        alerts = await fallback_storage.get_alerts(user_id=wallet_address)
        
        profile = {
            "user": user,
            "statistics": {
                "total_monitors": len(monitors),
                "active_monitors": len([m for m in monitors if m.enabled]),
                "total_alerts": len(alerts),
                "recent_alerts": len([a for a in alerts if (datetime.utcnow() - a.createdAt).days <= 7])
            },
            "preferences": getattr(user, 'notificationPreferences', {}),
            "account_age_days": (datetime.utcnow() - user.createdAt).days if user.createdAt else 0
        }
        
        return profile

@router.patch("/{wallet_address}/preferences")
async def update_user_preferences(wallet_address: str, preferences: Dict[str, bool]):
    """Update user notification preferences"""
    if is_connected():
        user = await User.find_one(User.walletAddress == wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update preferences
        current_prefs = user.notificationPreferences or {}
        current_prefs.update(preferences)
        
        await user.update({"$set": {
            "notificationPreferences": current_prefs,
            "updatedAt": datetime.utcnow()
        }})
        
        return {"message": "Preferences updated successfully", "preferences": current_prefs}
    else:
        user = await fallback_storage.get_user(wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update preferences in fallback storage
        current_prefs = getattr(user, 'notificationPreferences', {})
        current_prefs.update(preferences)
        
        await fallback_storage.update_user(wallet_address, {
            "notificationPreferences": current_prefs,
            "updatedAt": datetime.utcnow()
        })
        
        return {"message": "Preferences updated successfully", "preferences": current_prefs}
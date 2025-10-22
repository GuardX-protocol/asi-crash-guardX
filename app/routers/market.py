from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Dict, Any, Optional
from app.agents.crash_detector import get_agent, get_latest_alerts, run_crash_detection
from app.models import MarketAlert, AgentStatus
import asyncio

router = APIRouter()

agent_running = False
agent_task = None

@router.get("/status", response_model=AgentStatus)
async def get_market_status():
    alerts = get_latest_alerts()
    return AgentStatus(
        agent_running=agent_running,
        latest_alerts=[str(alert) for alert in alerts],
        message="Market crash detector status"
    )

@router.post("/start-agent")
async def start_crash_detector(background_tasks: BackgroundTasks):
    global agent_running, agent_task
    
    if agent_running:
        return {"message": "Agent is already running"}
    
    def run_agent():
        global agent_running
        agent_running = True
        try:
            agent = get_agent()
            agent.run()
        except Exception as e:
            print(f"Agent error: {e}")
        finally:
            agent_running = False
    
    background_tasks.add_task(run_agent)
    return {"message": "Market crash detector agent started"}

@router.post("/stop-agent")
async def stop_crash_detector():
    global agent_running, agent_task
    
    if not agent_running:
        return {"message": "Agent is not running"}
    
    agent_running = False
    return {"message": "Agent stop requested"}

@router.get("/alerts")
async def get_alerts():
    alerts = get_latest_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts)
    }

@router.post("/analyze")
async def analyze_market(symbol: Optional[str] = None, lookback: Optional[int] = None):
    try:
        result = run_crash_detection(symbol, lookback)
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str, lookback: Optional[int] = None):
    try:
        result = run_crash_detection(symbol, lookback)
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
Main entry point for the GuardX application
"""

from app.main import app

# For Deta Space deployment
application = app

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
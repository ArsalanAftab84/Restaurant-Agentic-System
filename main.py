from fastapi import FastAPI, Depends
from database import get_db_connection
from routers import menu, orders, reservations
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Restaurant Voice Agent API")

# Register the routers
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(reservations.router)

@app.get("/health")
def health_check(conn = Depends(get_db_connection)):
    """Liveness + DB check"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        db_status = "connected"
    except Exception as e:
        db_status = "disconnected"
        return {"data": None, "error": {"code": "DB_ERROR", "message": str(e)}}

    return {
        "data": {"status": "healthy", "database": db_status}, 
        "error": None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
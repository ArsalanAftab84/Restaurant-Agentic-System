from fastapi import Header, HTTPException
import os

def verify_webhook(x_webhook_secret: str = Header(None)):
    """Verifies the secret header from Vapi to prevent unauthorized access"""
    expected_secret = os.getenv("WEBHOOK_SECRET")
    
    if not x_webhook_secret or x_webhook_secret != expected_secret:
        # This properly stops the request and returns a 401 status code
        raise HTTPException(status_code=401, detail="Invalid Webhook Secret")
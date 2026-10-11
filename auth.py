from fastapi import Header
from schemas import APIResponse
import os

def verify_webhook(x_webhook_secret: str = Header(None)):
    """Verifies the secret header from Vapi/Retell to prevent unauthorized access"""
    expected_secret = os.getenv("WEBHOOK_SECRET")
    
    if not x_webhook_secret or x_webhook_secret != expected_secret:
        # We raise a standard Exception to be caught by our error envelope
        raise Exception("401_UNAUTHORIZED")
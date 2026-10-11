from fastapi import APIRouter, Depends
from schemas import APIResponse, OrderQuoteRequest, CreateOrderRequest
from database import get_db_connection
from auth import verify_webhook
import services

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/quote", response_model=APIResponse)
def quote_order(request: OrderQuoteRequest, conn = Depends(get_db_connection)):
    try:
        quote_data = services.calculate_order_quote(conn, request.items)
        return {"data": quote_data, "error": None}
    except Exception as e:
        return {"data": None, "error": {"code": "QUOTE_ERROR", "message": str(e)}}

@router.post("", response_model=APIResponse)
def create_order(
    request: CreateOrderRequest, 
    conn = Depends(get_db_connection),
    _=Depends(verify_webhook) # This locks the route behind our secret key
):
    """Create a new order. Requires X-Webhook-Secret header."""
    try:
        result = services.process_create_order(conn, request)
        return {"data": result, "error": None}
    except Exception as e:
        # Check if the error was our 401 Unauthorized trigger
        if str(e) == "401_UNAUTHORIZED":
            return {"data": None, "error": {"code": "UNAUTHORIZED", "message": "Invalid Webhook Secret"}}
            
        return {"data": None, "error": {"code": "ORDER_ERROR", "message": str(e)}}
from fastapi import APIRouter, Depends
from schemas import APIResponse, ReservationCreateRequest
from database import get_db_connection
from auth import verify_webhook
import services

router = APIRouter(prefix="/reservations", tags=["Reservations"])

@router.post("", response_model=APIResponse)
def create_reservation(
    request: ReservationCreateRequest, 
    conn = Depends(get_db_connection),
    _=Depends(verify_webhook)
):
    """Create a new reservation. Requires X-Webhook-Secret header."""
    try:
        # Hard check for party size limits (BR-R3)
        if request.party_size > 8: # Based on our seeded tables, 8 is the max
            return {"data": None, "error": {"code": "PARTY_TOO_LARGE", "message": "Please call for group bookings."}}

        result = services.process_create_reservation(conn, request)
        return {"data": result, "error": None}
        
    except Exception as e:
        error_msg = str(e)
        if error_msg == "401_UNAUTHORIZED":
            return {"data": None, "error": {"code": "UNAUTHORIZED", "message": "Invalid Webhook Secret"}}
        if error_msg == "409_NO_TABLE_AVAILABLE":
            return {"data": None, "error": {"code": "NO_TABLE_AVAILABLE", "message": "No tables available for this size at this time."}}
            
        return {"data": None, "error": {"code": "RESERVATION_ERROR", "message": error_msg}}
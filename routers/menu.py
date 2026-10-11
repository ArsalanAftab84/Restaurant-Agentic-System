from fastapi import APIRouter, Depends, Query
from schemas import APIResponse, MenuSearchRequest
from database import get_db_connection
import crud

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.post("", response_model=APIResponse)
def search_menu(
    request: MenuSearchRequest, 
    conn = Depends(get_db_connection)
):
    try:
        # Pass the values from the JSON body into our database search
        items = crud.get_filtered_menu(
            conn, 
            category=request.category, 
            available=True, # We only want to return available items to the AI
            dietary=request.dietary, 
            exclude_allergen=request.exclude_allergen, 
            q=request.q
        )
        return {"data": items, "error": None}
    except Exception as e:
        return {"data": None, "error": {"code": "DB_ERROR", "message": str(e)}}
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# Standard Response Envelope required by PRD
class APIResponse(BaseModel):
    data: Any
    error: Any = None

class MenuItem(BaseModel):
    item_id: int
    name: str
    description: Optional[str]
    category: str
    dietary_tags: List[str]
    contains_allergens: List[str]
    prep_minutes: int
    price_cents: int
    is_available: bool

class OrderItemInput(BaseModel):
    item_id: int
    quantity: int
    modifiers: Optional[str] = None

class OrderQuoteRequest(BaseModel):
    items: List[OrderItemInput]

class CreateOrderRequest(BaseModel):
    customer_name: str
    phone_number: str
    pickup_time: datetime
    items: List[OrderItemInput]
    special_instructions: Optional[str] = None
    allergy_note: Optional[str] = None

# Add to the bottom of schemas.py
class ReservationCreateRequest(BaseModel):
    guest_name: str
    phone_number: str
    party_size: int
    starts_at: datetime
    special_requests: Optional[str] = None

class MenuSearchRequest(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    dietary: Optional[str] = None
    exclude_allergen: Optional[str] = None
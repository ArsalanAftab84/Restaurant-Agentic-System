from datetime import datetime, timezone, timedelta
import crud

def calculate_order_quote(conn, items):
    settings = crud.get_restaurant_settings(conn)
    tax_rate = float(settings.get('tax_rate', 0.13))
    prep_base = int(settings.get('prep_minutes_base', 15))

    subtotal_cents = 0
    max_prep_time = 0
    total_quantity = 0
    validated_lines = []

    for req_item in items:
        db_item = crud.get_menu_item_by_id(conn, req_item.item_id)

        if not db_item:
            raise Exception(f"Item ID {req_item.item_id} does not exist.")
        if not db_item['is_available']:
            raise Exception(f"ITEM_UNAVAILABLE: {db_item['name']} is currently unavailable.")

        line_total = db_item['price_cents'] * req_item.quantity
        subtotal_cents += line_total
        total_quantity += req_item.quantity
        
        if db_item['prep_minutes'] > max_prep_time:
            max_prep_time = db_item['prep_minutes']

        validated_lines.append({
            "item_id": req_item.item_id,
            "name": db_item['name'],
            "unit_price_cents": db_item['price_cents'],
            "quantity": req_item.quantity,
            "modifiers": req_item.modifiers,
            "line_total_cents": line_total
        })

    tax_cents = int(round(subtotal_cents * tax_rate))
    total_cents = subtotal_cents + tax_cents

    extra_time_penalty = max(0, ((total_quantity - 1) // 4) * 5)
    total_prep_minutes = prep_base + max_prep_time + extra_time_penalty
    
    earliest_pickup = datetime.now(timezone.utc) + timedelta(minutes=total_prep_minutes)

    return {
        "validated_lines": validated_lines,
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "earliest_pickup_time": earliest_pickup.isoformat()
    }

# Add to the bottom of services.py

def process_create_reservation(conn, request):
    # 1. Calculate dwell time (BR-R2: 90 mins default, +30 mins for parties of 6+)
    settings = crud.get_restaurant_settings(conn)
    base_minutes = int(settings.get('reservation_minutes', 90))
    
    if request.party_size >= 6:
        base_minutes += 30
        
    ends_at = request.starts_at + timedelta(minutes=base_minutes)

    # 2. Find an available table (BR-R3)
    # The database will automatically check for overlaps and return the smallest valid table
    table = crud.find_available_table(conn, request.party_size, request.starts_at, ends_at)
    
    if not table:
        raise Exception("409_NO_TABLE_AVAILABLE")

    # 3. Prepare data and insert
    res_data = {
        "guest_name": request.guest_name,
        "phone_number": request.phone_number,
        "party_size": request.party_size,
        "starts_at": request.starts_at,
        "ends_at": ends_at,
        "table_id": table['table_id'],
        "special_requests": request.special_requests
    }

    new_res = crud.create_reservation_in_db(conn, res_data)
    
    return {
        "confirmation_code": new_res['confirmation_code'],
        "table_name": table['name'],
        "starts_at": request.starts_at.isoformat(),
        "ends_at": ends_at.isoformat()
    }

def process_create_order(conn, request):
    # 1. Idempotency Check (BR-07 related: no accidental duplicates)
    recent_order = crud.check_recent_order(conn, request.phone_number)
    if recent_order:
        return {"order_number": recent_order['order_number'], "message": "Existing order returned."}

    # 2. Re-calculate totals on the server securely
    quote = calculate_order_quote(conn, request.items)

    # 3. Handle allergy rule (BR-O5)
    allergy_flag = True if request.allergy_note else False

    # 4. Prepare data for DB
    order_data = {
        "customer_name": request.customer_name,
        "phone_number": request.phone_number,
        "pickup_time": request.pickup_time,
        "subtotal_cents": quote['subtotal_cents'],
        "tax_cents": quote['tax_cents'],
        "total_cents": quote['total_cents'],
        "special_instructions": request.special_instructions,
        "allergy_flag": allergy_flag,
        "allergy_note": request.allergy_note
    }

    # 5. Insert into DB
    new_order = crud.create_order_in_db(conn, order_data, quote['validated_lines'])
    
    return {
        "order_number": new_order['order_number'],
        "status": "received",
        "total_cents": quote['total_cents'],
        "pickup_time": request.pickup_time.isoformat()
    }
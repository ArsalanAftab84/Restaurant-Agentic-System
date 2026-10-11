from psycopg2.extras import RealDictCursor

def get_restaurant_settings(conn):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT key, value FROM restaurant_settings WHERE key IN ('tax_rate', 'prep_minutes_base')")
    settings = {row['key']: row['value'] for row in cur.fetchall()}
    cur.close()
    return settings

def get_menu_item_by_id(conn, item_id: int):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT name, price_cents, prep_minutes, is_available FROM menu_items WHERE item_id = %s", (item_id,))
    item = cur.fetchone()
    cur.close()
    return item

def get_filtered_menu(conn, category, available, dietary, exclude_allergen, q):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM menu_items WHERE 1=1"
    params = []

    if category:
        query += " AND category = %s"
        params.append(category)
    if available is not None:
        query += " AND is_available = %s"
        params.append(available)
    if dietary:
        query += " AND %s = ANY(dietary_tags)"
        params.append(dietary)
    if exclude_allergen:
        query += " AND NOT (%s = ANY(contains_allergens))"
        params.append(exclude_allergen)
    if q:
        query += " AND name ILIKE %s"
        params.append(f"%{q}%")

    query += " ORDER BY category, name"
    cur.execute(query, params)
    items = cur.fetchall()
    cur.close()
    return items

def check_recent_order(conn, phone_number: str):
    """Idempotency check: looks for an order from the same phone in the last 2 minutes"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT order_id, order_number FROM orders 
        WHERE phone_number = %s AND created_at > now() - interval '2 minutes'
    """, (phone_number,))
    record = cur.fetchone()
    cur.close()
    return record

def create_order_in_db(conn, order_data: dict, validated_lines: list):
    """Saves the main order and line items inside a single database transaction"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1. Insert main order and get the generated order_number
        cur.execute("""
            INSERT INTO orders (
                customer_name, phone_number, pickup_time, 
                subtotal_cents, tax_cents, total_cents, 
                special_instructions, allergy_flag, allergy_note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id, order_number
        """, (
            order_data['customer_name'], order_data['phone_number'], order_data['pickup_time'],
            order_data['subtotal_cents'], order_data['tax_cents'], order_data['total_cents'],
            order_data['special_instructions'], order_data['allergy_flag'], order_data['allergy_note']
        ))
        new_order = cur.fetchone()
        
        # 2. Insert all the individual items
        for line in validated_lines:
            cur.execute("""
                INSERT INTO order_items (
                    order_id, item_id, name_at_time_of_order, 
                    unit_price_cents, quantity, modifiers, line_total_cents
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                new_order['order_id'], line['item_id'], line['name'],
                line['unit_price_cents'], line['quantity'], line['modifiers'], line['line_total_cents']
            ))
        
        # 3. Commit the transaction
        conn.commit()
        cur.close()
        return new_order
    except Exception as e:
        conn.rollback() # If anything fails, undo the whole thing
        cur.close()
        raise e


# Add to the bottom of crud.py
def find_available_table(conn, party_size: int, starts_at, ends_at):
    """Finds the smallest available table that fits the party and has no overlaps (BR-R3)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # The gist constraint logic is handled natively using the overlaps operator (&&)
    cur.execute("""
        SELECT table_id, name, capacity 
        FROM restaurant_tables t
        WHERE is_active = true 
          AND capacity >= %s
          AND NOT EXISTS (
              SELECT 1 FROM reservations r
              WHERE r.table_id = t.table_id
                AND r.status IN ('confirmed', 'seated')
                AND tstzrange(r.starts_at, r.ends_at) && tstzrange(%s, %s)
          )
        ORDER BY capacity ASC, table_id ASC
        LIMIT 1
    """, (party_size, starts_at, ends_at))
    
    table = cur.fetchone()
    cur.close()
    return table

def create_reservation_in_db(conn, res_data: dict):
    """Saves the reservation and generates a short confirmation code."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Generate a simple 6-character alphanumeric code
        cur.execute("SELECT substring(md5(random()::text), 1, 6) AS code")
        code = cur.fetchone()['code'].upper()

        cur.execute("""
            INSERT INTO reservations (
                confirmation_code, guest_name, phone_number, party_size, 
                starts_at, ends_at, table_id, special_requests
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING reservation_id, confirmation_code
        """, (
            code, res_data['guest_name'], res_data['phone_number'], res_data['party_size'],
            res_data['starts_at'], res_data['ends_at'], res_data['table_id'],
            res_data['special_requests']
        ))
        new_res = cur.fetchone()
        conn.commit()
        cur.close()
        return new_res
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e
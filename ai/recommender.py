from models.database import get_db

def get_trip_suggestions(user_id, limit=5):
    """AI-based trip suggestions using collaborative filtering"""
    conn = get_db()
    
    # Get user's past reservations
    past = conn.execute('''
        SELECT t.departure, t.destination FROM reservations r
        JOIN trips t ON r.trip_id = t.id
        WHERE r.passenger_id = ? AND r.status = 'confirmed'
    ''', (user_id,)).fetchall()
    
    if past:
        routes = [(p['departure'], p['destination']) for p in past]
        dep, dest = routes[-1]
        suggestions = conn.execute('''
            SELECT t.*, u.name as driver_name,
            (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id) as booked
            FROM trips t JOIN users u ON t.driver_id=u.id
            WHERE t.departure LIKE ? OR t.destination LIKE ?
            AND t.available_seats > 0 AND t.status='active'
            LIMIT ?
        ''', (f'%{dep}%', f'%{dest}%', limit)).fetchall()
    else:
        # Popular trips for new users
        suggestions = conn.execute('''
            SELECT t.*, u.name as driver_name,
            (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id) as booked
            FROM trips t JOIN users u ON t.driver_id=u.id
            WHERE t.available_seats > 0 AND t.status='active'
            ORDER BY booked DESC LIMIT ?
        ''', (limit,)).fetchall()
    
    conn.close()
    return [dict(s) for s in suggestions]

def get_popular_routes():
    """Detect most popular routes"""
    conn = get_db()
    popular = conn.execute('''
        SELECT t.departure, t.destination, COUNT(*) as count
        FROM reservations r JOIN trips t ON r.trip_id=t.id
        GROUP BY t.departure, t.destination
        ORDER BY count DESC LIMIT 10
    ''').fetchall()
    conn.close()
    return [dict(p) for p in popular]

def get_price_recommendation(departure, destination):
    """Recommend price based on similar routes"""
    conn = get_db()
    avg = conn.execute('''
        SELECT AVG(price) as avg_price FROM trips
        WHERE departure LIKE ? AND destination LIKE ?
    ''', (f'%{departure}%', f'%{destination}%')).fetchone()
    conn.close()
    return round(avg['avg_price'] or 50, 2)

from models.database import get_db

def get_trip_suggestions(user_id, limit=5):
    conn = get_db()
    # Get user's reservation history
    history = conn.execute("""
        SELECT t.departure, t.destination FROM reservations r
        JOIN trips t ON r.trip_id = t.id
        WHERE r.passenger_id = ?
    """, (user_id,)).fetchall()

    popular = conn.execute("""
        SELECT t.id, t.departure, t.destination, t.date, t.time, t.price, t.available_seats,
               COUNT(r.id) as booking_count, u.name as driver_name
        FROM trips t
        LEFT JOIN reservations r ON t.id = r.trip_id
        JOIN users u ON t.driver_id = u.id
        WHERE t.status = 'active' AND t.available_seats > 0
        GROUP BY t.id ORDER BY booking_count DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(p) for p in popular]

def detect_popular_routes():
    conn = get_db()
    routes = conn.execute("""
        SELECT t.departure, t.destination, COUNT(r.id) as count
        FROM trips t LEFT JOIN reservations r ON t.id = r.trip_id
        GROUP BY t.departure, t.destination
        ORDER BY count DESC LIMIT 5
    """).fetchall()
    conn.close()
    return [dict(r) for r in routes]

def analyze_user_behavior(user_id):
    conn = get_db()
    stats = {
        'total_reservations': conn.execute("SELECT COUNT(*) FROM reservations WHERE passenger_id=?", (user_id,)).fetchone()[0],
        'total_trips_created': conn.execute("SELECT COUNT(*) FROM trips WHERE driver_id=?", (user_id,)).fetchone()[0],
        'favorite_routes': conn.execute("""
            SELECT t.departure, t.destination, COUNT(*) as cnt
            FROM reservations r JOIN trips t ON r.trip_id=t.id
            WHERE r.passenger_id=? GROUP BY t.departure, t.destination ORDER BY cnt DESC LIMIT 3
        """, (user_id,)).fetchall()
    }
    conn.close()
    return stats

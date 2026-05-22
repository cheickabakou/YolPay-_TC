from flask import Blueprint, render_template, session
from models.database import get_db
from utils.helpers import login_required
from ai.recommender import get_trip_suggestions

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    user_id = session['user_id']
    conn = get_db()
    reservations = conn.execute('''
        SELECT r.*, t.departure, t.destination, t.date, t.time, t.price, u.name as driver_name
        FROM reservations r JOIN trips t ON r.trip_id=t.id JOIN users u ON t.driver_id=u.id
        WHERE r.passenger_id=? ORDER BY r.created_at DESC LIMIT 5
    ''', (user_id,)).fetchall()
    my_trips = conn.execute('''
        SELECT t.*, (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id AND status='confirmed') as confirmed
        FROM trips t WHERE t.driver_id=? ORDER BY t.created_at DESC LIMIT 5
    ''', (user_id,)).fetchall()
    notifications = conn.execute('''
        SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 10
    ''', (user_id,)).fetchall()
    unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (user_id,)).fetchone()['c']
    activity = conn.execute('''
        SELECT * FROM activity_log WHERE user_id=? ORDER BY timestamp DESC LIMIT 10
    ''', (user_id,)).fetchall()
    conn.close()
    suggestions = get_trip_suggestions(user_id)
    return render_template('dashboard/index.html',
        reservations=[dict(r) for r in reservations],
        my_trips=[dict(t) for t in my_trips],
        notifications=[dict(n) for n in notifications],
        unread=unread,
        activity=[dict(a) for a in activity],
        suggestions=suggestions)

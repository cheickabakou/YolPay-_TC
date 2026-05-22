from flask import Blueprint, render_template, request
from models.database import get_db
from analytics.data_analysis import get_stats_overview

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    stats = get_stats_overview()
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, u.name as driver_name FROM trips t
        JOIN users u ON t.driver_id=u.id
        WHERE t.status='active' ORDER BY t.created_at DESC LIMIT 6
    ''').fetchall()
    conn.close()
    return render_template('public/index.html', stats=stats, trips=[dict(t) for t in trips])

@public_bp.route('/map')
def map_view():
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, u.name as driver_name FROM trips t
        JOIN users u ON t.driver_id=u.id WHERE t.status='active'
    ''').fetchall()
    conn.close()
    return render_template('public/map.html', trips=[dict(t) for t in trips])

@public_bp.route('/search')
def search():
    departure = request.args.get('departure','')
    destination = request.args.get('destination','')
    date = request.args.get('date','')
    seats = request.args.get('seats', 1, type=int)
    conn = get_db()
    query = '''SELECT t.*, u.name as driver_name,
        (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id AND status='confirmed') as booked
        FROM trips t JOIN users u ON t.driver_id=u.id
        WHERE t.status='active' AND t.available_seats >= ?'''
    params = [seats]
    if departure:
        query += ' AND t.departure LIKE ?'; params.append(f'%{departure}%')
    if destination:
        query += ' AND t.destination LIKE ?'; params.append(f'%{destination}%')
    if date:
        query += ' AND t.date = ?'; params.append(date)
    query += ' ORDER BY t.date, t.time'
    trips = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('public/search.html', trips=[dict(t) for t in trips],
                           departure=departure, destination=destination, date=date, seats=seats)

@public_bp.route('/about')
def about():
    return render_template('public/about.html')

@public_bp.route('/contact')
def contact():
    return render_template('public/contact.html')

@public_bp.route('/faq')
def faq():
    return render_template('public/faq.html')

@public_bp.route('/terms')
def terms():
    return render_template('public/terms.html')

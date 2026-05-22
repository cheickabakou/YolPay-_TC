from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import get_db, log_activity
from utils.helpers import login_required

passenger_bp = Blueprint('passenger', __name__)

@passenger_bp.route('/book/<int:trip_id>', methods=['POST'])
@login_required
def book(trip_id):
    user_id = session['user_id']
    conn = get_db()
    existing = conn.execute("SELECT id FROM reservations WHERE trip_id=? AND passenger_id=? AND status!='cancelled'",
                            (trip_id, user_id)).fetchone()
    if existing:
        flash('Bu yolculuğa zaten kayıtlısınız!', 'warning')
    else:
        trip = conn.execute("SELECT * FROM trips WHERE id=? AND status='active'", (trip_id,)).fetchone()
        if trip and trip['available_seats'] > 0:
            conn.execute("INSERT INTO reservations (trip_id,passenger_id,status) VALUES (?,?,?)",
                         (trip_id, user_id, 'pending'))
            conn.execute("UPDATE trips SET available_seats=available_seats-1 WHERE id=?", (trip_id,))
            conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)",
                         (trip['driver_id'], f'Yeni rezervasyon isteği aldınız: {trip["departure"]} → {trip["destination"]}'))
            conn.commit()
            log_activity(user_id, 'book_trip', f'Trip ID: {trip_id}')
            flash('Rezervasyon isteği gönderildi!', 'success')
        else:
            flash('Bu yolculuk için yer kalmadı.', 'danger')
    conn.close()
    return redirect(url_for('dashboard.index'))

@passenger_bp.route('/cancel/<int:res_id>', methods=['POST'])
@login_required
def cancel(res_id):
    user_id = session['user_id']
    conn = get_db()
    res = conn.execute("SELECT * FROM reservations WHERE id=? AND passenger_id=?", (res_id, user_id)).fetchone()
    if res:
        conn.execute("UPDATE reservations SET status='cancelled' WHERE id=?", (res_id,))
        conn.execute("UPDATE trips SET available_seats=available_seats+1 WHERE id=?", (res['trip_id'],))
        conn.commit()
        flash('Rezervasyon iptal edildi.', 'info')
    conn.close()
    return redirect(url_for('dashboard.index'))

@passenger_bp.route('/history')
@login_required
def history():
    user_id = session['user_id']
    conn = get_db()
    reservations = conn.execute('''
        SELECT r.*, t.departure, t.destination, t.date, t.time, t.price, u.name as driver_name
        FROM reservations r JOIN trips t ON r.trip_id=t.id JOIN users u ON t.driver_id=u.id
        WHERE r.passenger_id=? ORDER BY r.created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('dashboard/history.html', reservations=[dict(r) for r in reservations])

@passenger_bp.route('/favorite/<int:trip_id>', methods=['POST'])
@login_required
def toggle_favorite(trip_id):
    user_id = session['user_id']
    conn = get_db()
    fav = conn.execute("SELECT id FROM favorites WHERE user_id=? AND trip_id=?", (user_id, trip_id)).fetchone()
    if fav:
        conn.execute("DELETE FROM favorites WHERE user_id=? AND trip_id=?", (user_id, trip_id))
        msg = 'Favorilerden çıkarıldı.'
    else:
        conn.execute("INSERT INTO favorites (user_id,trip_id) VALUES (?,?)", (user_id, trip_id))
        msg = 'Favorilere eklendi!'
    conn.commit()
    conn.close()
    flash(msg, 'info')
    return redirect(request.referrer or url_for('dashboard.index'))

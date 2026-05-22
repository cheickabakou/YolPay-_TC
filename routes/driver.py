from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import get_db, log_activity
from utils.helpers import login_required, role_required

driver_bp = Blueprint('driver', __name__)

@driver_bp.route('/')
@role_required('driver','admin')
def dashboard():
    user_id = session['user_id']
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id AND status='confirmed') as confirmed,
        (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id AND status='pending') as pending_count
        FROM trips t WHERE t.driver_id=? ORDER BY t.created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('dashboard/driver.html', trips=[dict(t) for t in trips])

@driver_bp.route('/create', methods=['GET','POST'])
@role_required('driver','admin')
def create_trip():
    if request.method == 'POST':
        data = request.form
        conn = get_db()
        conn.execute('''INSERT INTO trips (driver_id,departure,destination,departure_lat,departure_lng,
            destination_lat,destination_lng,date,time,price,available_seats,description)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (session['user_id'], data['departure'], data['destination'],
             data.get('dep_lat',0), data.get('dep_lng',0),
             data.get('dest_lat',0), data.get('dest_lng',0),
             data['date'], data['time'], data['price'],
             data['available_seats'], data.get('description','')))
        conn.commit()
        conn.close()
        log_activity(session['user_id'], 'create_trip', f"{data['departure']} -> {data['destination']}")
        flash('Yolculuk başarıyla oluşturuldu!', 'success')
        return redirect(url_for('driver.dashboard'))
    return render_template('dashboard/create_trip.html')

@driver_bp.route('/trip/<int:trip_id>/edit', methods=['GET','POST'])
@role_required('driver','admin')
def edit_trip(trip_id):
    conn = get_db()
    trip = conn.execute("SELECT * FROM trips WHERE id=? AND driver_id=?", (trip_id, session['user_id'])).fetchone()
    if not trip:
        flash('Yolculuk bulunamadı!', 'danger')
        return redirect(url_for('driver.dashboard'))
    if request.method == 'POST':
        data = request.form
        conn.execute('''UPDATE trips SET departure=?,destination=?,date=?,time=?,price=?,
            available_seats=?,description=? WHERE id=?''',
            (data['departure'],data['destination'],data['date'],data['time'],
             data['price'],data['available_seats'],data.get('description',''),trip_id))
        conn.commit()
        conn.close()
        flash('Yolculuk güncellendi!', 'success')
        return redirect(url_for('driver.dashboard'))
    conn.close()
    return render_template('dashboard/edit_trip.html', trip=dict(trip))

@driver_bp.route('/trip/<int:trip_id>/delete', methods=['POST'])
@role_required('driver','admin')
def delete_trip(trip_id):
    conn = get_db()
    conn.execute("UPDATE trips SET status='cancelled' WHERE id=? AND driver_id=?", (trip_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Yolculuk iptal edildi.', 'info')
    return redirect(url_for('driver.dashboard'))

@driver_bp.route('/trip/<int:trip_id>/passengers')
@role_required('driver','admin')
def passengers(trip_id):
    conn = get_db()
    trip = conn.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
    pax = conn.execute('''
        SELECT r.*, u.name, u.email FROM reservations r JOIN users u ON r.passenger_id=u.id
        WHERE r.trip_id=? ORDER BY r.created_at DESC
    ''', (trip_id,)).fetchall()
    conn.close()
    return render_template('dashboard/passengers.html', trip=dict(trip), passengers=[dict(p) for p in pax])

@driver_bp.route('/reservation/<int:res_id>/<action>', methods=['POST'])
@role_required('driver','admin')
def manage_reservation(res_id, action):
    if action not in ['confirmed','rejected']:
        flash('Geçersiz işlem', 'danger')
        return redirect(url_for('driver.dashboard'))
    conn = get_db()
    res = conn.execute("SELECT * FROM reservations WHERE id=?", (res_id,)).fetchone()
    if res:
        conn.execute("UPDATE reservations SET status=? WHERE id=?", (action, res_id))
        msg = 'Rezervasyonunuz onaylandı!' if action=='confirmed' else 'Rezervasyonunuz reddedildi.'
        conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)", (res['passenger_id'], msg))
        conn.commit()
    conn.close()
    flash('İşlem tamamlandı.', 'success')
    return redirect(url_for('driver.passengers', trip_id=res['trip_id']))

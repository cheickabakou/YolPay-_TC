from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import get_db, log_activity
from utils.helpers import role_required
from analytics.data_analysis import get_stats_overview, get_trips_by_month, get_top_routes, get_user_role_distribution

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@role_required('admin')
def dashboard():
    stats = get_stats_overview()
    trips_by_month = get_trips_by_month()
    top_routes = get_top_routes()
    role_dist = get_user_role_distribution()
    conn = get_db()
    logs = conn.execute('''
        SELECT a.*, u.name, u.email FROM activity_log a
        LEFT JOIN users u ON a.user_id=u.id ORDER BY a.timestamp DESC LIMIT 50
    ''').fetchall()
    conn.close()
    return render_template('admin/dashboard.html', stats=stats,
        trips_by_month=trips_by_month, top_routes=top_routes,
        role_dist=role_dist, logs=[dict(l) for l in logs])

@admin_bp.route('/users')
@role_required('admin')
def users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin/users.html', users=[dict(u) for u in users])

@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@role_required('admin')
def change_role(user_id):
    new_role = request.form.get('role')
    if new_role in ['admin','driver','passenger','urban']:
        conn = get_db()
        conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        conn.commit()
        conn.close()
        log_activity(session['user_id'], 'change_role', f'User {user_id} -> {new_role}')
        flash('Rol güncellendi!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    log_activity(session['user_id'], 'delete_user', f'User {user_id} deleted')
    flash('Kullanıcı silindi.', 'warning')
    return redirect(url_for('admin.users'))

@admin_bp.route('/trips')
@role_required('admin')
def trips():
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, u.name as driver_name,
        (SELECT COUNT(*) FROM reservations WHERE trip_id=t.id) as total_res
        FROM trips t JOIN users u ON t.driver_id=u.id ORDER BY t.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/trips.html', trips=[dict(t) for t in trips])

@admin_bp.route('/reservations')
@role_required('admin')
def reservations():
    conn = get_db()
    res = conn.execute('''
        SELECT r.*, t.departure, t.destination, t.date, u.name as passenger_name, d.name as driver_name
        FROM reservations r JOIN trips t ON r.trip_id=t.id
        JOIN users u ON r.passenger_id=u.id JOIN users d ON t.driver_id=d.id
        ORDER BY r.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/reservations.html', reservations=[dict(r) for r in res])

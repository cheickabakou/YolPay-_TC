from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import get_db, hash_password, verify_password, log_activity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            log_activity(user['id'], 'login', f'Giriş yapıldı: {email}')
            flash(f'Hoş geldiniz, {user["name"]}!', 'success')
            role_redirects = {
                'admin': 'admin.dashboard',
                'driver': 'driver.dashboard',
                'urban': 'urban.dashboard',
            }
            return redirect(url_for(role_redirects.get(user['role'], 'dashboard.index')))
        flash('E-posta veya şifre hatalı!', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        role = request.form.get('role','passenger')
        if role not in ['passenger','driver']:
            role = 'passenger'
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash('Bu e-posta zaten kayıtlı!', 'danger')
            conn.close()
            return render_template('auth/register.html')
        conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                     (name, email, hash_password(password), role))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        log_activity(user['id'], 'register', f'Yeni kayıt: {email}')
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'logout', 'Çıkış yapıldı')
    session.clear()
    flash('Çıkış yapıldı.', 'info')
    return redirect(url_for('public.index'))

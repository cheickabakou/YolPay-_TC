from flask import Flask, jsonify, request, session, render_template, redirect, url_for, send_from_directory, Response
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "copilote_secret_key_2026"

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'yolpayi.db')

from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            role       TEXT    NOT NULL CHECK(role IN ('admin','driver','passenger','urban')),
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            from_node   TEXT    NOT NULL,
            to_node     TEXT    NOT NULL,
            from_name   TEXT,
            to_name     TEXT,
            distance    REAL    DEFAULT 0,
            duration    INTEGER DEFAULT 0,
            passengers  INTEGER DEFAULT 1,
            intensity   TEXT    CHECK(intensity IN ('high','med','low')) DEFAULT 'med',
            status      TEXT    CHECK(status IN ('active','done')) DEFAULT 'active',
            date        TEXT,
            week_count  INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type       TEXT,
            message    TEXT,
            user_id    INTEGER,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

with app.app_context():
    init_db()


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    return dict(user) if user else None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/auth/register', methods=['POST'])
def register():
    data     = request.get_json()
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role     = data.get('role', 'passenger')

    if not name or not email or not password:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Şifre çok kısa (en az 6 karakter)'}), 400
    if role not in ('admin', 'driver', 'passenger', 'urban'):
        return jsonify({'error': 'Rôle invalide'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Bu e-posta adresi zaten kullanılıyor'}), 409

    hashed     = hash_password(password)
    created_at = datetime.now().strftime('%Y-%m-%d')
    db.execute(
        'INSERT INTO users (name, email, password, role, created_at) VALUES (?,?,?,?,?)',
        (name, email, hashed, role, created_at)
    )
    db.commit()
    user = dict(db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone())
    session['user_id']   = user['id']
    session['user_role'] = user['role']

    db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
               ('o', f'Yeni hesap oluşturuldu : <strong>{name}</strong>', user['id'], 'Az önce'))
    db.commit()

    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']
    }})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'E-posta ve şifre gereklidir'}), 400

    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user or dict(user)['password'] != hash_password(password):
        return jsonify({'error': 'E-posta veya şifre hatalı'}), 401

    user = dict(user)
    session['user_id']   = user['id']
    session['user_role'] = user['role']

    db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
               ('b', f'Giriş yapıldı : <strong>{user["name"]}</strong>', user['id'], 'Az önce'))
    db.commit()

    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']
    }})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user = get_current_user()
    if user:
        db = get_db()
        db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
                   ('r', f'Çıkış yapıldı : <strong>{user["name"]}</strong>', user['id'], 'Az önce'))
        db.commit()
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me')
def me():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Non authentifié'}), 401
    return jsonify({'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']}})



@app.route('/api/trips', methods=['GET'])
@login_required
def get_trips():
    db   = get_db()
    user = get_current_user()
    role = user['role']
    intensity = request.args.get('intensity', '')
    status    = request.args.get('status', '')

    query      = 'SELECT t.*, u.name as driver_name FROM trips t JOIN users u ON t.user_id=u.id'
    params     = []
    conditions = []

    if role in ('driver', 'passenger'):
        conditions.append('t.user_id=?')
        params.append(user['id'])
    if intensity:
        conditions.append('t.intensity=?')
        params.append(intensity)
    if status:
        conditions.append('t.status=?')
        params.append(status)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY t.id DESC'

    trips = [dict(r) for r in db.execute(query, params).fetchall()]
    return jsonify({'trips': trips, 'total': len(trips)})


@app.route('/api/trips', methods=['POST'])
@login_required
def create_trip():
    user = get_current_user()
    if user['role'] == 'urban':
        return jsonify({'error': 'Accès refusé : gestionnaire en lecture seule'}), 403

    data       = request.get_json()
    from_node  = data.get('from_node', '').upper()
    to_node    = data.get('to_node', '').upper()
    distance   = float(data.get('distance', 0))
    passengers = int(data.get('passengers', 1))
    intensity  = data.get('intensity', 'med')
    from_name  = data.get('from_name', from_node)
    to_name    = data.get('to_name', to_node)

    if not from_node or not to_node:
        return jsonify({'error': 'Nœuds invalides'}), 400
    if from_node == to_node:
        return jsonify({'error': 'Départ et arrivée identiques'}), 400
    if distance <= 0:
        return jsonify({'error': 'Distance invalide'}), 400

    duration = round(distance / 30 * 60)
    date     = datetime.now().strftime('%Y-%m-%d')

    db = get_db()
    db.execute(
        '''INSERT INTO trips (user_id, from_node, to_node, from_name, to_name,
           distance, duration, passengers, intensity, status, date, week_count)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (user['id'], from_node, to_node, from_name, to_name,
         distance, duration, passengers, intensity, 'active', date, 0)
    )
    db.commit()
    trip = db.execute('SELECT * FROM trips ORDER BY id DESC LIMIT 1').fetchone()

    db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
               ('o', f'Yeni yolculuk : <strong>{from_name} → {to_name}</strong> ({passengers} yolcu)',
                user['id'], 'Az önce'))
    db.commit()
    return jsonify({'success': True, 'trip': dict(trip)}), 201


@app.route('/api/trips/<int:trip_id>', methods=['PUT'])
@login_required
def update_trip(trip_id):
    user = get_current_user()
    db   = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id=?', (trip_id,)).fetchone()
    if not trip:
        return jsonify({'error': 'Trajet introuvable'}), 404
    trip = dict(trip)

    if user['role'] != 'admin' and trip['user_id'] != user['id']:
        return jsonify({'error': 'Accès refusé'}), 403

    data       = request.get_json()
    from_node  = data.get('from_node', trip['from_node']).upper()
    to_node    = data.get('to_node',   trip['to_node']).upper()
    distance   = float(data.get('distance',   trip['distance']))
    passengers = int(data.get('passengers',   trip['passengers']))
    intensity  = data.get('intensity', trip['intensity'])
    status     = data.get('status',    trip['status'])
    from_name  = data.get('from_name', from_node)
    to_name    = data.get('to_name',   to_node)
    duration   = round(distance / 30 * 60)

    db.execute(
        '''UPDATE trips SET from_node=?, to_node=?, from_name=?, to_name=?,
           distance=?, duration=?, passengers=?, intensity=?, status=? WHERE id=?''',
        (from_node, to_node, from_name, to_name, distance, duration, passengers, intensity, status, trip_id)
    )
    db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
               ('b', f'Yolculuk <strong>#{trip_id}</strong> güncellendi', user['id'], 'Az önce'))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/trips/<int:trip_id>', methods=['DELETE'])
@login_required
def delete_trip(trip_id):
    user = get_current_user()
    db   = get_db()
    trip = db.execute('SELECT * FROM trips WHERE id=?', (trip_id,)).fetchone()
    if not trip:
        return jsonify({'error': 'Trajet introuvable'}), 404
    trip = dict(trip)

    if user['role'] != 'admin' and trip['user_id'] != user['id']:
        return jsonify({'error': 'Accès refusé'}), 403

    db.execute('DELETE FROM trips WHERE id=?', (trip_id,))
    db.execute("INSERT INTO activity_log (type, message, user_id, created_at) VALUES (?,?,?,?)",
               ('r', f'Yolculuk <strong>{trip["from_name"]} → {trip["to_name"]}</strong> silindi',
                user['id'], 'Az önce'))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/users')
@login_required
def get_users():
    user = get_current_user()
    if user['role'] not in ('admin', 'urban'):
        return jsonify({'error': 'Accès refusé'}), 403
    db    = get_db()
    users = [dict(u) for u in db.execute('SELECT id,name,email,role,created_at FROM users ORDER BY id').fetchall()]
    for u in users:
        u['trip_count'] = db.execute('SELECT COUNT(*) FROM trips WHERE user_id=?', (u['id'],)).fetchone()[0]
    return jsonify({'users': users})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = get_current_user()
    if user['role'] != 'admin':
        return jsonify({'error': 'Accès refusé'}), 403
    if user_id == user['id']:
        return jsonify({'error': 'Impossible de supprimer votre propre compte'}), 400
    db = get_db()
    db.execute('DELETE FROM trips WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/activity')
@login_required
def get_activity():
    db    = get_db()
    limit = int(request.args.get('limit', 10))
    logs  = [dict(r) for r in db.execute(
        'SELECT * FROM activity_log ORDER BY id DESC LIMIT ?', (limit,)
    ).fetchall()]
    return jsonify({'activity': logs})


@app.route('/api/stats/summary')
@login_required
def stats_summary():
    import pandas as pd
    conn  = sqlite3.connect(DB_PATH)
    try:
        df_t = pd.read_sql_query('SELECT t.*, u.role as driver_role FROM trips t LEFT JOIN users u ON t.user_id=u.id', conn)
        df_u = pd.read_sql_query('SELECT * FROM users', conn)
    except Exception:
        df_t = pd.DataFrame()
        df_u = pd.DataFrame()
    conn.close()

    if df_t.empty:
        return jsonify({'total_trips':0,'active_trips':0,'done_trips':0,'total_users':0,
                        'total_distance':0,'total_passengers':0,'co2_saved_kg':0,'avg_distance':0,'avg_passengers':0})

    total_dist = float(df_t['distance'].sum())
    total_pass = int(df_t['passengers'].sum())
    co2_saved  = round(total_dist * 0.12, 2)
    active     = int((df_t['status'] == 'active').sum())

    return jsonify({
        'total_trips':      int(len(df_t)),
        'active_trips':     active,
        'done_trips':       int(len(df_t)) - active,
        'total_users':      int(len(df_u)),
        'drivers':          int((df_u['role'] == 'driver').sum()) if not df_u.empty else 0,
        'passengers':       int((df_u['role'] == 'passenger').sum()) if not df_u.empty else 0,
        'urban':            int((df_u['role'] == 'urban').sum()) if not df_u.empty else 0,
        'total_distance':   round(total_dist, 1),
        'total_passengers': total_pass,
        'co2_saved_kg':     co2_saved,
        'avg_distance':     round(float(df_t['distance'].mean()), 2),
        'avg_passengers':   round(float(df_t['passengers'].mean()), 1),
    })


@app.route('/api/stats/weekly')
@login_required
def stats_weekly():
    import pandas as pd
    days = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
    base = [145,192,168,241,228,89,71]
    df   = pd.DataFrame({'day': days, 'trips': base})
    df['co2']      = (df['trips'] * 0.42).round(2)
    df['peak_pct'] = df['trips'].apply(lambda x: round(x / df['trips'].max() * 100, 1))
    return jsonify({'weekly': df.to_dict(orient='records')})


@app.route('/api/stats/intensity')
@login_required
def stats_intensity():
    import pandas as pd
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query('SELECT intensity FROM trips', conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        return jsonify({'intensity': {'high':0,'med':0,'low':0}})
    counts = df['intensity'].value_counts().to_dict()
    total  = len(df)
    return jsonify({'intensity': {
        'high': counts.get('high',0), 'med': counts.get('med',0), 'low': counts.get('low',0),
        'high_pct': round(counts.get('high',0)/total*100,1) if total else 0,
        'med_pct':  round(counts.get('med', 0)/total*100,1) if total else 0,
        'low_pct':  round(counts.get('low', 0)/total*100,1) if total else 0,
    }})


@app.route('/api/stats/nodes')
@login_required
def stats_nodes():
    import pandas as pd
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query('SELECT from_node, to_node FROM trips', conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        return jsonify({'nodes': []})
    from_c   = df['from_node'].value_counts()
    to_c     = df['to_node'].value_counts()
    combined = (from_c.add(to_c, fill_value=0)).sort_values(ascending=False)
    total    = combined.sum()
    return jsonify({'nodes': [
        {'node': k, 'count': int(v), 'pct': round(v/total*100,1)}
        for k, v in combined.items()
    ]})


@app.route('/api/stats/co2')
@login_required
def stats_co2():
    import pandas as pd
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query('SELECT distance, intensity FROM trips', conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        return jsonify({'total_co2_kg':0,'avg_co2_per_trip':0})
    df['co2_kg']    = df['distance'] * 0.12
    total           = round(float(df['co2_kg'].sum()), 2)
    avg             = round(float(df['co2_kg'].mean()), 3)
    by_intensity    = df.groupby('intensity')['co2_kg'].sum().round(2).to_dict()
    return jsonify({
        'total_co2_kg':     total,
        'avg_co2_per_trip': avg,
        'by_intensity':     by_intensity,
        'trees_equivalent': round(total / 0.5),
        'formula':          'CO₂ = distance(km) × 120g/km',
    })



NODES = {
    'A': {'id':'A','name':'Centre-Ville',   'lat':40.4600,'lng':39.4800,'type':'hub'},
    'B': {'id':'B','name':'Gare Centrale',  'lat':40.4550,'lng':39.4700,'type':'hub'},
    'C': {'id':'C','name':'Université',     'lat':40.4680,'lng':39.4900,'type':'place'},
    'D': {'id':'D','name':'Hôpital',        'lat':40.4520,'lng':39.4950,'type':'place'},
    'E': {'id':'E','name':'Marché Central', 'lat':40.4640,'lng':39.4650,'type':'place'},
    'F': {'id':'F','name':'Aéroport',       'lat':40.4450,'lng':39.4600,'type':'hub'},
    'G': {'id':'G','name':'Zone Nord',      'lat':40.4750,'lng':39.4830,'type':'zone'},
    'H': {'id':'H','name':'Zone Sud',       'lat':40.4490,'lng':39.4870,'type':'zone'},
    'I': {'id':'I','name':'Parc Industriel','lat':40.4600,'lng':39.5000,'type':'zone'},
    'J': {'id':'J','name':'Résidence Est',  'lat':40.4670,'lng':39.5050,'type':'zone'},
}
EDGES = [
    ('A','B',2.1),('A','C',3.4),('A','E',1.8),
    ('B','F',4.2),('B','H',2.8),
    ('C','G',2.0),('C','J',3.1),
    ('D','H',1.5),('D','I',2.6),
    ('E','B',1.4),('E','D',3.0),
    ('F','H',3.3),
    ('G','A',2.2),('G','I',4.0),
    ('H','I',2.1),
    ('I','J',1.9),
    ('J','C',3.2),
]

def build_graph():
    import networkx as nx
    G = nx.Graph()
    for nid, data in NODES.items():
        G.add_node(nid, **data)
    for u, v, w in EDGES:
        G.add_edge(u, v, weight=w)
    return G

G = build_graph()

@app.route('/api/graph/nodes')
@login_required
def get_nodes():
    return jsonify({'nodes': NODES})

@app.route('/api/graph/edges')
@login_required
def get_edges():
    return jsonify({'edges': [{'from': u, 'to': v, 'weight': w} for u, v, w in EDGES]})

@app.route('/api/graph/dijkstra', methods=['POST'])
@login_required
def run_dijkstra():
    import networkx as nx
    data    = request.get_json()
    from_id = data.get('from_node', '').upper()
    to_id   = data.get('to_node', '').upper()

    if from_id not in G or to_id not in G:
        return jsonify({'error': 'Nœuds invalides'}), 400
    try:
        path = nx.dijkstra_path(G, from_id, to_id, weight='weight')
        dist = nx.dijkstra_path_length(G, from_id, to_id, weight='weight')
        steps = []
        cumul = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            w     = G[u][v]['weight']
            cumul += w
            steps.append({
                'from': u, 'from_name': NODES[u]['name'],
                'to':   v, 'to_name':   NODES[v]['name'],
                'segment_km': round(w, 2),
                'cumul_km':   round(cumul, 2),
            })
        return jsonify({
            'path':        path,
            'distance':    round(dist, 2),
            'duration':    round(dist / 30 * 60),
            'steps':       steps,
            'nodes_count': len(path),
            'from_name':   NODES[from_id]['name'],
            'to_name':     NODES[to_id]['name'],
            'algorithm':   'Dijkstra (NetworkX)',
        })
    except nx.NetworkXNoPath:
        return jsonify({'error': 'Aucun chemin trouvé'}), 404



@app.route('/api/export/csv')
@login_required
def export_csv():
    import pandas as pd
    conn  = sqlite3.connect(DB_PATH)
    trips = pd.read_sql_query('SELECT * FROM trips ORDER BY id DESC', conn)
    conn.close()
    if trips.empty:
        trips = pd.DataFrame(columns=['id','from_name','to_name','distance','duration','passengers','intensity','status','date'])
    csv_data = trips.to_csv(index=False, encoding='utf-8')
    return Response(csv_data, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=yolpayi_yolculuklar.csv'})


@app.route('/api/db/info')
@login_required
def db_info():
    user = get_current_user()
    if user['role'] not in ('admin', 'urban'):
        return jsonify({'error': 'Accès refusé'}), 403
    db = get_db()
    return jsonify({
        'users_count':    db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'trips_count':    db.execute('SELECT COUNT(*) FROM trips').fetchone()[0],
        'activity_count': db.execute('SELECT COUNT(*) FROM activity_log').fetchone()[0],
        'db_file':        'yolpayi.db (SQLite)',
        'schema': {
            'users':        ['id','name','email','password','role','created_at'],
            'trips':        ['id','user_id','from_node','to_node','from_name','to_name','distance','duration','passengers','intensity','status','date','week_count'],
            'activity_log': ['id','type','message','user_id','created_at'],
        }
    })


@app.route('/api/db/reset', methods=['POST'])
@login_required
def db_reset():
    user = get_current_user()
    if user['role'] != 'admin':
        return jsonify({'error': 'Admin seulement'}), 403
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    session.clear()
    return jsonify({'success': True, 'message': 'Base de données réinitialisée'})


if __name__ == '__main__':
   
    app.run(debug=True, port=5000)

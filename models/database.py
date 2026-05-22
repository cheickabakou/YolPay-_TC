import sqlite3
import hashlib
from datetime import datetime

DB_PATH = 'database.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'passenger',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER NOT NULL,
        departure TEXT NOT NULL,
        destination TEXT NOT NULL,
        departure_lat REAL,
        departure_lng REAL,
        destination_lat REAL,
        destination_lng REAL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        price REAL NOT NULL,
        available_seats INTEGER NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (driver_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        passenger_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips(id),
        FOREIGN KEY (passenger_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trip_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (trip_id) REFERENCES trips(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Create admin user if not exists
    admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute("SELECT id FROM users WHERE email='admin@yolpayi.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ('Admin','admin@yolpayi.com', admin_pw, 'admin'))

    # Create sample driver
    driver_pw = hashlib.sha256('driver123'.encode()).hexdigest()
    c.execute("SELECT id FROM users WHERE email='driver@yolpayi.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ('Ahmet Yılmaz','driver@yolpayi.com', driver_pw, 'driver'))

    # Create sample urban manager
    urban_pw = hashlib.sha256('urban123'.encode()).hexdigest()
    c.execute("SELECT id FROM users WHERE email='urban@yolpayi.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ('Kent Yöneticisi','urban@yolpayi.com', urban_pw, 'urban'))

    # Sample trips
    c.execute("SELECT COUNT(*) as cnt FROM trips")
    if c.fetchone()['cnt'] == 0:
        sample_trips = [
            (2,'Gümüşhane','Trabzon',40.4597,39.4826,41.0015,39.7178,'2024-12-20','08:00',50,3,'Konforlu yolculuk',40.4597,39.4826),
            (2,'Trabzon','Erzurum',41.0015,39.7178,39.9055,41.2658,'2024-12-21','09:00',80,4,'Güvenli sürüş',41.0015,39.7178),
            (2,'Gümüşhane','Ankara',40.4597,39.4826,39.9334,32.8597,'2024-12-22','07:00',120,2,'Sabah erken yolculuk',40.4597,39.4826),
            (2,'Samsun','Trabzon',41.2867,36.3300,41.0015,39.7178,'2024-12-23','10:00',60,3,'Sahil yolu',41.2867,36.3300),
            (2,'Rize','Gümüşhane',41.0201,40.5234,40.4597,39.4826,'2024-12-24','11:00',45,2,'Dağ yolu',41.0201,40.5234),
        ]
        for t in sample_trips:
            c.execute('''INSERT INTO trips (driver_id,departure,destination,
                departure_lat,departure_lng,destination_lat,destination_lng,
                date,time,price,available_seats,description) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (t[0],t[1],t[2],t[3],t[4],t[5],t[6],t[7],t[8],t[9],t[10],t[11]))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def log_activity(user_id, action, details=None, ip_address=None):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (user_id,action,details,ip_address) VALUES (?,?,?,?)",
                 (user_id, action, details, ip_address))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hashlib.sha256(password.encode()).hexdigest() == hashed

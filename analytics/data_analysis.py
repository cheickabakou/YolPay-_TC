import json
from models.database import get_db

def get_stats_overview():
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
    trips = conn.execute("SELECT COUNT(*) as c FROM trips WHERE status='active'").fetchone()['c']
    reservations = conn.execute("SELECT COUNT(*) as c FROM reservations WHERE status='confirmed'").fetchone()['c']
    co2 = reservations * 2.3  # kg CO2 saved per shared ride
    conn.close()
    return {'users': users, 'trips': trips, 'reservations': reservations, 'co2_saved': round(co2,1)}

def get_trips_by_month():
    conn = get_db()
    data = conn.execute('''
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM trips GROUP BY month ORDER BY month DESC LIMIT 12
    ''').fetchall()
    conn.close()
    return [dict(d) for d in data]

def get_top_routes():
    conn = get_db()
    data = conn.execute('''
        SELECT departure, destination, COUNT(*) as count, AVG(price) as avg_price
        FROM trips GROUP BY departure, destination ORDER BY count DESC LIMIT 10
    ''').fetchall()
    conn.close()
    return [dict(d) for d in data]

def get_user_role_distribution():
    conn = get_db()
    data = conn.execute('''
        SELECT role, COUNT(*) as count FROM users GROUP BY role
    ''').fetchall()
    conn.close()
    return [dict(d) for d in data]

def get_reservation_stats():
    conn = get_db()
    data = conn.execute('''
        SELECT status, COUNT(*) as count FROM reservations GROUP BY status
    ''').fetchall()
    conn.close()
    return [dict(d) for d in data]

def get_network_graph():
    """Build city network for Dijkstra visualization"""
    import networkx as nx
    conn = get_db()
    trips = conn.execute("SELECT departure, destination, price FROM trips WHERE status='active'").fetchall()
    conn.close()
    G = nx.DiGraph()
    for t in trips:
        G.add_edge(t['departure'], t['destination'], weight=t['price'])
    nodes = [{'id': n, 'label': n} for n in G.nodes()]
    edges = [{'from': u, 'to': v, 'weight': d['weight']} for u,v,d in G.edges(data=True)]
    return {'nodes': nodes, 'edges': edges}

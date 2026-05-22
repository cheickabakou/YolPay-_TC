import networkx as nx
from models.database import get_db

def get_global_stats():
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    trips = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    reservations = conn.execute("SELECT COUNT(*) FROM reservations WHERE status='confirmed'").fetchone()[0]
    conn.close()
    co2 = reservations * 2.3 * 150  # avg 150km, 2.3kg CO2/km saved per shared seat
    return {'users': users, 'trips': trips, 'reservations': reservations, 'co2_saved': round(co2, 1)}

def dijkstra_route(departure, destination):
    conn = get_db()
    trips = conn.execute("SELECT departure, destination, price FROM trips WHERE status='active'").fetchall()
    conn.close()
    G = nx.DiGraph()
    for t in trips:
        G.add_edge(t['departure'], t['destination'], weight=t['price'])
    try:
        path = nx.dijkstra_path(G, departure, destination, weight='weight')
        cost = nx.dijkstra_path_length(G, departure, destination, weight='weight')
        return {'path': path, 'cost': round(cost, 2), 'found': True}
    except:
        return {'path': [], 'cost': 0, 'found': False}

def get_urban_analytics():
    conn = get_db()
    routes = conn.execute("""
        SELECT departure, destination, COUNT(*) as trips_count,
               SUM(available_seats) as total_seats
        FROM trips GROUP BY departure, destination ORDER BY trips_count DESC LIMIT 10
    """).fetchall()
    monthly = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM trips GROUP BY month ORDER BY month DESC LIMIT 6
    """).fetchall()
    conn.close()
    return {
        'routes': [dict(r) for r in routes],
        'monthly': [dict(m) for m in monthly]
    }

def get_eco_stats():
    conn = get_db()
    total_res = conn.execute("SELECT COUNT(*) FROM reservations WHERE status='confirmed'").fetchone()[0]
    conn.close()
    avg_km = 150
    co2_per_km = 0.21
    total_co2_saved = total_res * avg_km * co2_per_km
    trees_equiv = total_co2_saved / 21
    return {
        'co2_saved_kg': round(total_co2_saved, 1),
        'trees_equivalent': round(trees_equiv, 1),
        'km_shared': total_res * avg_km
    }

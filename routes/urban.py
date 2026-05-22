from flask import Blueprint, render_template
from utils.helpers import role_required
from analytics.data_analysis import get_stats_overview, get_top_routes, get_trips_by_month, get_network_graph

urban_bp = Blueprint('urban', __name__)

@urban_bp.route('/')
@role_required('urban','admin')
def dashboard():
    stats = get_stats_overview()
    top_routes = get_top_routes()
    trips_by_month = get_trips_by_month()
    network = get_network_graph()
    return render_template('dashboard/urban.html', stats=stats,
        top_routes=top_routes, trips_by_month=trips_by_month, network=network)

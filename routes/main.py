from flask import Blueprint, render_template
from services.data_loader import load_nodes
from services.nmos_connection import load_receivers_and_sources
from services.cache import read_cache

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    cache = read_cache()
    return render_template(
        'index.html',
        receivers=cache['receivers'],
        sources=cache['sources'],
        nodes=cache['nodes'],
        node_count=len(cache['nodes']),
        receiver_count=len(cache['receivers']),
        source_count=len(cache['sources']),
        selected_receiver_id=None,
        selected_source_id=None
    )
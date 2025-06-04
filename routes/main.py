from flask import Blueprint, render_template
from services.data_loader import load_nodes
from services.nmos_connection import load_receivers_and_sources

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    nodes = load_nodes()
    receivers, sources = load_receivers_and_sources(nodes)
    
    return render_template(
        'index.html',
        receivers=receivers,
        sources=sources,
        nodes=nodes,
        receiver_count=len(receivers),
        source_count=len(sources),
        node_count=len(nodes),
        selected_receiver_id=None,
        selected_source_id=None
    )

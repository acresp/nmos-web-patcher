from flask import Blueprint, request, jsonify, render_template
from services.data_loader import load_nodes, save_nodes
from services.nmos_discovery import detect_nmos_and_connection_versions

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        new_nodes = request.json
        save_nodes(new_nodes)
        return jsonify({"status": "success", "message": "Nodes updated"})
    return render_template('settings.html', nodes=load_nodes())

@settings_bp.route('/detect_versions', methods=['POST'])
def detect_versions():
    data = request.json
    node_url = data['url']
    versions = detect_nmos_and_connection_versions(node_url)
    if versions["nmos"] and versions["connection"]:
        return jsonify({"status": "success", "versions": versions})
    else:
        return jsonify({"status": "error", "message": f"Detected versions: {versions}"}), 500

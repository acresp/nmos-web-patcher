from flask import Blueprint, request, jsonify, render_template
from services.data_loader import load_nodes, save_nodes
from services.nmos_discovery import detect_nmos_and_connection_versions
import json

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        new_nodes = request.json
        save_nodes(new_nodes)
        return jsonify({"status": "success", "message": "Nodes updated"})

    try:
        with open("settings.json") as f:
            refresh_interval = json.load(f).get("refresh_interval", 600)

    except:
        refresh_interval = 10

    return render_template(
        'settings.html',
        nodes=load_nodes(),
        refresh_interval=refresh_interval
    )


@settings_bp.route('/detect_versions', methods=['POST'])
def detect_versions():
    data = request.json
    node_url = data['url']
    versions = detect_nmos_and_connection_versions(node_url)
    if versions["nmos"] and versions["connection"]:
        return jsonify({"status": "success", "versions": versions})
    else:
        return jsonify({"status": "error", "message": f"Detected versions: {versions}"}), 500

@settings_bp.route('/refresh_cache')
def refresh_cache():
    from services.cache import refresh_discovery
    refresh_discovery()
    return jsonify({"status": "ok", "message": "Cache refreshed"})

@settings_bp.route('/update_refresh_interval', methods=['POST'])
def update_refresh_interval():
    try:
        data = request.json
        interval = int(data.get("refresh_interval", 600))
        with open("settings.json", "r") as f:
            settings_data = json.load(f)
        settings_data["refresh_interval"] = interval
        with open("settings.json", "w") as f:
            json.dump(settings_data, f, indent=2)
        return jsonify({"status": "success", "message": "Refresh interval updated."})
    except Exception as e:
        print(f"[ERROR] Failed to save refresh interval: {e}")
        return jsonify({"status": "error", "message": "Failed to save refresh interval"}), 500

def load_refresh_interval():
    try:
        with open("settings.json") as f:
            settings = json.load(f)
            interval = int(settings.get("refresh_interval", 600))
            print(f"[DEBUG] Loaded refresh interval from settings.json: {interval} seconds")
            return interval
    except Exception as e:
        print(f"[WARNING] Could not load refresh interval, using default 600. Error: {e}")
        return 600

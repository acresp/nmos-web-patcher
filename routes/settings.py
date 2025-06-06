from flask import Blueprint, request, jsonify, render_template
from services.data_loader import load_nodes, save_nodes
from services.nmos_discovery import detect_nmos_and_connection_versions
import json

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def settings():
    try:
        with open("settings.json") as f:
            settings = json.load(f)
            refresh_interval = settings.get("refresh_interval", 600)
            patch_secondary = settings.get("patch_secondary", False)
    except:
        refresh_interval = 600
        patch_secondary = False

    return render_template(
        'settings.html',
        nodes=load_nodes(),
        refresh_interval=refresh_interval,
        patch_secondary=patch_secondary
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

@settings_bp.route('/update_settings', methods=['POST'])
def update_settings():
    try:
        data = request.json

        with open("settings.json", "r") as f:
            settings_data = json.load(f)

        if "refresh_interval" in data:
            settings_data["refresh_interval"] = int(data["refresh_interval"])
        if "patch_secondary" in data:
            settings_data["patch_secondary"] = bool(data["patch_secondary"])

        with open("settings.json", "w") as f:
            json.dump(settings_data, f, indent=2)

        return jsonify({"status": "success", "message": "Settings updated."})
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")
        return jsonify({"status": "error", "message": "Failed to save settings"}), 500

def load_settings():
    default_settings = {
        "refresh_interval": 600,
        "patch_secondary": True
    }

    try:
        with open("settings.json", "r") as f:
            file_settings = json.load(f)
            merged = {**default_settings, **file_settings}
            return merged
    except Exception as e:
        print(f"[WARNING] Could not load settings.json, using defaults. Error: {e}")
        return default_settings

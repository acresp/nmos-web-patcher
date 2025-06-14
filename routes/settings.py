# /routes/settings.py
# by Arnaud Cresp - 2025

from flask import Blueprint, request, jsonify, render_template, redirect
from services.data_loader import load_nodes, save_nodes
from services.nmos_discovery import detect_nmos_and_connection_versions
from services.cache import read_cache as load_cache
from services.logical import load_logical_ids, save_logical_ids
import json
import asyncio
import builtins

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def settings():
    settings_data = load_settings()
    refresh_interval = settings_data.get("refresh_interval")
    patch_secondary = settings_data.get("patch_secondary")
    enable_restapi = settings_data.get("enable_restapi")
    enable_bmd_emulator = settings_data.get("enable_bmd_emulator")

    cache = load_cache()
    senders = cache.get("sources", [])
    receivers = cache.get("receivers", [])

    return render_template(
        'settings.html',
        nodes=load_nodes(),
        refresh_interval=refresh_interval,
        patch_secondary=patch_secondary,
        enable_restapi=enable_restapi,
        enable_bmd_emulator=enable_bmd_emulator,
        senders=senders,
        receivers=receivers
    )

@settings_bp.route('/settings/save_nodes', methods=['POST'])
def save_nodes_route():
    try:
        nodes = request.get_json()
        save_nodes(nodes)
        print(f"[SETTINGS] Saved {len(nodes)} nodes to nodes.json")

        from services.cache import refresh_discovery
        refresh_discovery()
        print("[SETTINGS] Discovery cache refreshed after node save")

        return jsonify({"status": "success", "message": "Nodes saved and cache refreshed."})
    except Exception as e:
        print(f"[ERROR] Failed to save nodes: {e}")
        return jsonify({"status": "error", "message": "Failed to save nodes"}), 500

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

        old_bmd = settings_data.get("enable_bmd_emulator", False)

        settings_data["refresh_interval"] = int(data.get("refresh_interval", 600))
        settings_data["patch_secondary"] = bool(data.get("patch_secondary", False))
        settings_data["enable_restapi"] = bool(data.get("enable_restapi", False))
        settings_data["enable_bmd_emulator"] = bool(data.get("enable_bmd_emulator", False))

        new_bmd = settings_data["enable_bmd_emulator"]

        print("[DEBUG] Writing updated settings:", settings_data)

        with open("settings.json", "w") as f:
            json.dump(settings_data, f, indent=2)

        if old_bmd != new_bmd:
            loop = getattr(builtins, "main_event_loop", None)
            if loop:
                if new_bmd:
                    from protocols.bmdvideohub import VideohubEmulator
                    emulator = VideohubEmulator()
                    builtins.emulator_instance = emulator
                    asyncio.run_coroutine_threadsafe(emulator.start(), loop)
                    print("[SETTINGS] BMD Emulator started dynamically")
                else:
                    emulator = getattr(builtins, "emulator_instance", None)
                    if emulator:
                        asyncio.run_coroutine_threadsafe(emulator.stop(), loop)
                        builtins.emulator_instance = None
                        print("[SETTINGS] BMD Emulator stopped dynamically")

        return jsonify({"status": "success", "message": "Settings updated."})
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")
        return jsonify({"status": "error", "message": "Failed to save settings"}), 500

@settings_bp.route('/logical', methods=['GET'], endpoint='logical_page')
def logical_page():
    from services.cache import read_cache
    from services.logical import load_logical_ids
    from services.nmos_discovery import get_resource_type

    cache = read_cache()
    senders = cache.get("sources", [])
    receivers = cache.get("receivers", [])
    logical_ids = load_logical_ids()

    for s in senders:
        s["essence_type"] = get_resource_type(s)
    for r in receivers:
        r["essence_type"] = get_resource_type(r)

    return render_template("logical.html",
                           senders=senders,
                           receivers=receivers,
                           logical_ids=logical_ids)

@settings_bp.route("/settings/logical_ids", methods=["POST"])
def add_logical_id():
    logical_name = request.form.get("logical_name")
    entry_type = request.form.get("entry_type")
    video = request.form.get("video")
    audio = request.form.get("audio")
    data = request.form.get("data")
    submitted_id = request.form.get("logical_id")

    logicals = load_logical_ids()
    logicals.setdefault(entry_type, {})

    used_ids = [v["id"] for v in logicals[entry_type].values() if "id" in v]

    if submitted_id:
        group_id = int(submitted_id)
        if group_id in used_ids:
            return f"Error: ID {group_id} already in use for {entry_type}", 400
    else:
        group_id = max(used_ids, default=0) + 1

    logicals[entry_type][logical_name] = {
        "id": group_id
    }
    if video:
        logicals[entry_type][logical_name]["video"] = video
    if audio:
        logicals[entry_type][logical_name]["audio"] = audio
    if data:
        logicals[entry_type][logical_name]["data"] = data

    save_logical_ids(logicals)

    emulator = getattr(builtins, "emulator_instance", None)
    loop = getattr(builtins, "main_event_loop", None)

    if emulator and loop:
        try:
            asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)
            print("[SETTINGS] BMD Emulator reloaded after logical update.")
        except Exception as e:
            print(f"[SETTINGS] Failed to notify emulator: {e}")

    return redirect("/logical")

@settings_bp.route('/settings/delete_logical_id', methods=['POST'])
def delete_logical_id():
    logical_name = request.form.get("logical_name")
    entry_type = request.form.get("entry_type")

    logicals = load_logical_ids()

    if entry_type in logicals and logical_name in logicals[entry_type]:
        del logicals[entry_type][logical_name]
        save_logical_ids(logicals)
        print(f"[INFO] Deleted logical group: {entry_type} → {logical_name}")

    emulator = getattr(builtins, "emulator_instance", None)
    loop = getattr(builtins, "main_event_loop", None)

    if emulator and loop:
        try:
            asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)
            print("[SETTINGS] BMD Emulator reloaded after logical update.")
        except Exception as e:
            print(f"[SETTINGS] Failed to notify emulator: {e}")

    return redirect("/logical")

@settings_bp.route('/settings/update_logical_id', methods=['POST'])
def update_logical_id():
    original_name = request.form.get("original_name")
    logical_name  = request.form.get("logical_name")
    entry_type    = request.form.get("entry_type")
    video         = request.form.get("video") or None
    audio         = request.form.get("audio") or None
    data          = request.form.get("data")  or None
    logical_id    = int(request.form.get("logical_id"))

    logicals = load_logical_ids()

    for name, entry in logicals[entry_type].items():
        if name != original_name and entry.get("id") == logical_id:
            return f"Error: ID {logical_id} already in use for {entry_type}", 400

    if logical_name != original_name:
        logicals[entry_type][logical_name] = logicals[entry_type].pop(original_name)
    else:
        logical_name = original_name

    logicals[entry_type][logical_name]["id"] = logical_id
    logicals[entry_type][logical_name]["video"] = video
    logicals[entry_type][logical_name]["audio"] = audio
    logicals[entry_type][logical_name]["data"]  = data

    save_logical_ids(logicals)

    emulator = getattr(builtins, "emulator_instance", None)
    loop = getattr(builtins, "main_event_loop", None)

    if emulator and loop:
        try:
            asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)
            print("[SETTINGS] BMD Emulator reloaded after logical update.")
        except Exception as e:
            print(f"[SETTINGS] Failed to notify emulator: {e}")

    return redirect("/logical")

def load_settings():
    default_settings = {
        "refresh_interval": 300,
        "patch_secondary": True,
        "enable_restapi": True,
        "enable_bmd_emulator": False
    }

    try:
        with open("settings.json", "r") as f:
            file_settings = json.load(f)
            merged = {**default_settings, **file_settings}
            return merged
    except Exception as e:
        print(f"[WARNING] Could not load settings.json, using defaults. Error: {e}")
        return default_settings

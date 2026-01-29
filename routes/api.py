# /routes/api.py
# by Arnaud Cresp - 2025

import asyncio
import builtins
import threading
from flask import Blueprint, request, jsonify
from services.data_loader import load_nodes
from services.nmos_connection import change_source, disconnect_receiver
from services.cache import refresh_discovery

api_bp = Blueprint('api', __name__)

@api_bp.route('/refresh_cache')
def api_refresh_cache():
    def do_refresh():
        try:
            refresh_discovery()
            print("[INFO] Cache refreshed successfully.")
        except Exception as e:
            print(f"[ERROR] Cache refresh failed: {e}")

    threading.Thread(target=do_refresh, daemon=True).start()
    return jsonify({"status": "in_progress", "message": "Cache refresh started in background."})

@api_bp.route('/change_source', methods=['POST'])
def api_change_source():
    data = request.json
    receiver_id = data.get('receiver_id')
    sender_id = data.get('sender_id')

    if not receiver_id or not sender_id:
        return jsonify({"status": "error", "message": "Missing receiver or sender ID"}), 400

    nodes = load_nodes()

    loop = getattr(builtins, "main_event_loop", None)
    if not loop:
        return jsonify({"status": "error", "message": "Asyncio main loop not available"}), 500

    try:
        future = asyncio.run_coroutine_threadsafe(
            change_source(nodes, receiver_id, sender_id),
            loop
        )
        result = future.result(timeout=5)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify(result), (200 if result["status"] == "success" else result.get("code", 500))

@api_bp.route('/disconnect_receiver', methods=['POST'])
def api_disconnect_receiver():
    data = request.json
    receiver_id = data.get('receiver_id')

    if not receiver_id:
        return jsonify({"status": "error", "message": "Missing receiver ID"}), 400

    from services.cache import read_cache

    nodes = load_nodes()
    cache = read_cache()
    receivers = cache.get("receivers", [])

    result = disconnect_receiver(nodes, receiver_id, receivers=receivers)
    return jsonify(result), (200 if result.get("status") == "success" else result.get("code", 500))

@api_bp.route("/get_current_sender/<receiver_id>")
def get_current_sender(receiver_id):
    from services.cache import read_cache
    from services.data_loader import load_nodes
    from services.nmos_discovery import safe_get_json

    cache = read_cache()
    nodes = load_nodes()

    receivers = cache.get("receivers", [])
    receiver_obj = next((r for r in receivers if r.get("id") == receiver_id), None)
    if not receiver_obj:
        return jsonify({"label": "Unknown", "message": "Receiver not found"}), 404

    node_name = receiver_obj.get("node_name")
    node_info = next((n for n in nodes if n.get("name") == node_name), None)
    if not node_info:
        return jsonify({"label": "Unknown", "message": f"Node {node_name} not found"}), 404

    base_url = (node_info.get("url") or "").rstrip("/")
    if base_url.endswith("/x-nmos"):
        base_url = base_url.rsplit("/x-nmos", 1)[0]

    connection_version = (
        node_info.get("versions", {}).get("connection")
        or node_info.get("connection")
        or "v1.1"
    )

    active_url = f"{base_url}/x-nmos/connection/{connection_version}/single/receivers/{receiver_id}/active/"

    try:
        active_data = safe_get_json(active_url, timeout=2)

        sender_id = (
            active_data.get("transport_params", [{}])[0].get("sender_id")
            or active_data.get("sender_id")
        )

        if not sender_id:
            return jsonify({
                "label": "None",
                "sender_id": None,
                "message": "Receiver has no active sender"
            }), 200

        senders_list = cache.get("senders") or cache.get("sources", [])
        sender_obj = next((s for s in senders_list if s.get("id") == sender_id), None)
        label = sender_obj.get("label", sender_id) if sender_obj else sender_id

        return jsonify({
            "label": label,
            "sender_id": sender_id,
            "message": f"Fetched from {connection_version} NMOS endpoint"
        }), 200

    except Exception as e:
        print(f"[WARN] Fallback to cache for receiver {receiver_id}: {e}")
        sender_id = receiver_obj.get("subscription", {}).get("sender_id")

        senders_list = cache.get("senders", [])
        sender_label = next(
            (s.get("label") for s in senders_list if s.get("id") == sender_id),
            sender_id
        )

        return jsonify({
            "label": sender_label or "Unknown",
            "sender_id": sender_id,
            "message": f"Fallback cache (error: {e})"
        }), 200
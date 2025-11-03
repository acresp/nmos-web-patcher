# /protocols/restapi.py
# by Arnaud Cresp - 2025

from flask import Blueprint, jsonify, request
import json
from functools import wraps
import asyncio
import builtins

restapi_bp = Blueprint("restapi", __name__)

def rest_api_enabled_only():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with open("settings.json") as fh:
                    settings = json.load(fh)
                if not settings.get("enable_restapi", False):
                    return jsonify({
                        "status": "error",
                        "message": "REST API is disabled in settings"
                    }), 403
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Could not load settings: {str(e)}"
                }), 500
            return func(*args, **kwargs)
        return wrapper
    return decorator

@restapi_bp.route("/api/take", methods=["GET"])
@rest_api_enabled_only()
def take_logical():
    from services.logical import load_logical_ids
    from services.patch_bus import emit_patch

    src_id = request.args.get("src")
    dest_id = request.args.get("dest")

    if not src_id or not dest_id:
        return jsonify({"status": "error", "message": "Missing src or dest"}), 400

    try:
        src_id = int(src_id)
        dest_id = int(dest_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid src or dest ID"}), 400

    logical = load_logical_ids()

    source_name = next((name for name, val in logical.get("sources", {}).items() if val.get("id") == src_id), None)
    destination_name = next((name for name, val in logical.get("receivers", {}).items() if val.get("id") == dest_id), None)

    if not source_name or not destination_name:
        return jsonify({"status": "error", "message": "Invalid src or dest ID"}), 404

    loop = getattr(builtins, "main_event_loop", None)
    if not loop:
        return jsonify({"status": "error", "message": "Asyncio main loop not available"}), 500

    try:
        future = asyncio.run_coroutine_threadsafe(
            emit_patch(src_id, dest_id, origin="REST"),
            loop
        )
        patched = future.result(timeout=5)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to emit patch: {str(e)}"}), 500

    def essence_status_bit(info):
        return "1" if info.get("status") in ["success", "patched"] else "0"

    patch_code = (
        essence_status_bit(patched.get("video", {})) +
        essence_status_bit(patched.get("audio", {})) +
        essence_status_bit(patched.get("data", {}))
    )

    try:
        videohub_emulator = getattr(builtins, "videohub_emulator", None)
        if videohub_emulator:
            future = asyncio.run_coroutine_threadsafe(
                videohub_emulator.set_routing(src_id, dest_id, origin="REST", force_broadcast=True),
                loop
            )
            future.result(timeout=3)
            print(f"[RESTAPI] Notified Videohub Emulator: {dest_id} ← {src_id}")
        else:
            print("[RESTAPI] Videohub Emulator not present")
    except Exception as e:
        print(f"[RESTAPI] Failed to notify Videohub Emulator: {e}")

    return jsonify({
        "status": "ok",
        "source_name": source_name,
        "destination_name": destination_name,
        "patch_code": patch_code,
        "patched": patched
    })

# API List Function
@restapi_bp.route("/api/list", methods=["GET"])
@rest_api_enabled_only()
def list_logical_groups():
    from services.logical import load_logical_ids

    try:
        logical = load_logical_ids()
        sources = [
            {"id": val.get("id"), "name": name}
            for name, val in logical.get("sources", {}).items()
        ]
        receivers = [
            {"id": val.get("id"), "name": name}
            for name, val in logical.get("receivers", {}).items()
        ]
        return jsonify({
            "status": "ok",
            "sources": sorted(sources, key=lambda x: x["id"]),
            "receivers": sorted(receivers, key=lambda x: x["id"])
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
# API Disconnect Function
@restapi_bp.route("/api/disconnect", methods=["GET"])
@rest_api_enabled_only()
def disconnect_logical():
    from services.logical import load_logical_ids
    from services.data_loader import load_nodes
    from services.nmos_connection import disconnect_receiver

    dest_id = request.args.get("dest")
    if not dest_id:
        return jsonify({"status": "error", "message": "Missing dest"}), 400

    try:
        dest_id = int(dest_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid dest ID"}), 400

    logical = load_logical_ids()
    dest_name = next((name for name, val in logical.get("receivers", {}).items()
                      if val.get("id") == dest_id), None)

    if not dest_name:
        return jsonify({"status": "error", "message": "Receiver group not found"}), 404

    dest = logical["receivers"][dest_name]
    nodes = load_nodes()
    result = {}

    for essence in ["video", "audio", "data"]:
        receiver_id = dest.get(essence)
        if receiver_id:
            try:
                r = disconnect_receiver(nodes, receiver_id)
                result[essence] = {
                    "status": r.get("status"),
                    "receiver": receiver_id,
                    "message": r.get("message", "")
                }
            except Exception as e:
                result[essence] = {
                    "status": "error",
                    "receiver": receiver_id,
                    "message": str(e)
                }
        else:
            result[essence] = {
                "status": "skipped",
                "reason": "No receiver ID defined"
            }

    return jsonify({
        "status": "ok",
        "receiver_name": dest_name,
        "disconnected": result
    })

# API Take_Many Function
@restapi_bp.route("/api/take_many", methods=["GET"])
@rest_api_enabled_only()
def take_many():
    from services.logical import load_logical_ids
    from services.patch_bus import emit_patch

    src_id = request.args.get("src")
    dest_ids = request.args.get("dest")

    if not src_id or not dest_ids:
        return jsonify({"status": "error", "message": "Missing src or dest"}), 400

    try:
        src_id = int(src_id)
        dest_ids = [int(d.strip()) for d in dest_ids.split(",")]
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid ID format"}), 400

    logical = load_logical_ids()

    src_name = next((name for name, val in logical["sources"].items() if val.get("id") == src_id), None)
    if not src_name:
        return jsonify({"status": "error", "message": "Invalid source ID"}), 404

    loop = getattr(builtins, "main_event_loop", None)
    if not loop:
        return jsonify({"status": "error", "message": "Asyncio main loop not available"}), 500

    responses = []

    for dest_id in dest_ids:
        dest_name = next((name for name, val in logical["receivers"].items() if val.get("id") == dest_id), None)

        if not dest_name:
            responses.append({
                "dest_id": dest_id,
                "receiver_name": None,
                "status": "error",
                "message": "Invalid receiver ID"
            })
            continue

        try:
            future = asyncio.run_coroutine_threadsafe(
                emit_patch(src_id, dest_id, origin="REST"),
                loop
            )
            patched = future.result(timeout=5)
        except Exception as e:
            responses.append({
                "dest_id": dest_id,
                "receiver_name": dest_name,
                "status": "error",
                "message": str(e),
                "patched": {}
            })
            continue

        def essence_status_bit(info):
            return "1" if info.get("status") in ["success", "patched"] else "0"

        patch_code = (
            essence_status_bit(patched.get("video", {})) +
            essence_status_bit(patched.get("audio", {})) +
            essence_status_bit(patched.get("data", {}))
        )

        responses.append({
            "dest_id": dest_id,
            "receiver_name": dest_name,
            "patch_code": patch_code,
            "patched": patched,
            "status": "ok"
        })

    return jsonify({
        "status": "ok",
        "source_name": src_name,
        "results": responses
    })

# API Dest Status Function
@restapi_bp.route("/api/status", methods=["GET"])
@rest_api_enabled_only()
def status_logical():
    import requests
    from services.cache import read_cache
    from services.logical import load_logical_ids

    dest_id = request.args.get("dest")
    if not dest_id:
        return jsonify({"status": "error", "message": "Missing dest"}), 400

    try:
        dest_id = int(dest_id)
    except:
        return jsonify({"status": "error", "message": "Invalid dest ID"}), 400

    logicals = load_logical_ids()
    cache = read_cache()
    receivers = cache.get("receivers", [])

    receiver_name = None
    logical_receiver = None
    for name, val in logicals["receivers"].items():
        if val.get("id") == dest_id:
            receiver_name = name
            logical_receiver = val
            break

    if not receiver_name or not logical_receiver:
        return jsonify({"status": "error", "message": "Logical receiver not found"}), 404

    active_result = {}
    active_sender_ids = {}
    for essence in ["video", "audio", "data"]:
        receiver_uuid = logical_receiver.get(essence)
        if not receiver_uuid:
            continue

        receiver = next((r for r in receivers if r.get("id") == receiver_uuid), None)
        if not receiver:
            continue

        node_url = receiver.get('node_url')
        version = receiver.get('versions', {}).get('connection', 'v1.1')
        url = f"{node_url}/connection/{version}/single/receivers/{receiver_uuid}/active/"

        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                sender_id = r.json().get("sender_id")
                if sender_id:
                    active_sender_ids[essence] = sender_id
                    active_result[essence] = {"sender_id": sender_id}
                else:
                    active_result[essence] = {"sender_id": None}
            else:
                active_result[essence] = {"sender_id": None, "error": "request failed"}
        except Exception as e:
            active_result[essence] = {"sender_id": None, "error": str(e)}

    matched_source = None
    for source_name, source_map in logicals["sources"].items():
        if all(source_map.get(k) == active_sender_ids.get(k) for k in ["video", "audio", "data"] if source_map.get(k)):
            matched_source = source_name
            break

    return jsonify({
        "status": "ok",
        "receiver_name": receiver_name,
        "active": active_result,
        "source_name": matched_source
    })
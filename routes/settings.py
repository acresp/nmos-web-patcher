# /routes/settings.py
# by Arnaud Cresp - 2025

from flask import Blueprint, request, jsonify, render_template, redirect
from services.data_loader import load_nodes, save_nodes
from services.nmos_discovery import detect_nmos_and_connection_versions, get_resource_type
from services.cache import read_cache as load_cache
from services.logical import load_logical_ids, save_logical_ids

import json
import asyncio
import builtins
from collections import defaultdict
import re

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def settings():
    settings_data = load_settings()

    cache = load_cache()
    senders = cache.get("senders", [])
    receivers = cache.get("receivers", [])

    return render_template(
        'settings.html',
        nodes=load_nodes(),
        refresh_interval=settings_data.get("refresh_interval"),
        patch_secondary=settings_data.get("patch_secondary"),
        enable_restapi=settings_data.get("enable_restapi"),
        enable_bmd_emulator=settings_data.get("enable_bmd_emulator"),
        enable_rosstalk_emulator=settings_data.get("enable_rosstalk_emulator"),
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
        old_ross = settings_data.get("enable_rosstalk_emulator", False)

        settings_data["refresh_interval"] = int(data.get("refresh_interval", 600))
        settings_data["patch_secondary"] = bool(data.get("patch_secondary", False))
        settings_data["enable_restapi"] = bool(data.get("enable_restapi", False))
        settings_data["enable_bmd_emulator"] = bool(data.get("enable_bmd_emulator", False))
        settings_data["enable_rosstalk_emulator"] = bool(data.get("enable_rosstalk_emulator", False))

        new_bmd = settings_data["enable_bmd_emulator"]
        new_ross = settings_data["enable_rosstalk_emulator"]

        with open("settings.json", "w") as f:
            json.dump(settings_data, f, indent=2)

        loop = getattr(builtins, "main_event_loop", None)

        if loop:
            if old_bmd != new_bmd:
                if new_bmd:
                    from protocols.bmdvideohub import VideohubEmulator
                    emulator = VideohubEmulator()
                    builtins.videohub_emulator = emulator
                    asyncio.run_coroutine_threadsafe(emulator.start(), loop)
                else:
                    emulator = getattr(builtins, "videohub_emulator", None)
                    if emulator:
                        asyncio.run_coroutine_threadsafe(emulator.stop(), loop)
                        builtins.videohub_emulator = None

            if old_ross != new_ross:
                if new_ross:
                    from protocols.rosstalk import RossTalkEmulator
                    emulator = RossTalkEmulator()
                    builtins.rosstalk_emulator = emulator
                    asyncio.run_coroutine_threadsafe(emulator.start(), loop)
                else:
                    emulator = getattr(builtins, "rosstalk_emulator", None)
                    if emulator:
                        asyncio.run_coroutine_threadsafe(emulator.stop(), loop)
                        builtins.rosstalk_emulator = None

        return jsonify({"status": "success", "message": "Settings updated."})

    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")
        return jsonify({"status": "error", "message": "Failed to save settings"}), 500

@settings_bp.route('/logical', methods=['GET'], endpoint='logical_page')
def logical_page():
    cache = load_cache()

    flows = cache.get("flows", [])
    flows_index = {f['id']: f for f in flows}

    senders = cache.get("sources", []) if cache.get("sources") else cache.get("senders", [])
    receivers = cache.get("receivers", [])

    for s in senders:
        s["essence_type"] = (
            s.get("type")
            or s.get("essence")
            or get_resource_type(s, flows_index)
        )
    for r in receivers:
        r["essence_type"] = (
            r.get("type")
            or r.get("essence")
            or get_resource_type(r, flows_index)
        )

    def parse_label_sortkey(label):
        try:
            m = re.search(r"\[(\d+),(\d+),(\d+)\]", label)
            sfx = re.search(r"\](\d{2})", label)
            if m:
                a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                a, b, c = 999, 999, 999
            
            s = int(sfx.group(1)) if sfx else 0
            return (a, b, c, s, label.lower())
        except Exception:
            return (999, 999, 999, 999, label.lower())

    senders.sort(key=lambda x: (
        x.get("node_name") or "zzz",
        *parse_label_sortkey(x.get("label", ""))
    ))

    receivers.sort(key=lambda x: (
        x.get("node_name") or "zzz",
        *parse_label_sortkey(x.get("label", ""))
    ))

    grouped_senders = defaultdict(list)
    for s in senders:
        node_name = s.get("node_name") or "Unknown Node"
        grouped_senders[node_name].append(s)

    logical_ids = load_logical_ids()

    return render_template(
        "logical.html",
        senders=senders,
        grouped_senders=dict(grouped_senders),
        receivers=receivers,
        logical_ids=logical_ids
    )

def next_contiguous_id(used_ids):
    used = sorted(set(used_ids))
    for i, val in enumerate(used):
        if i != val:
            return i
    return len(used)

@settings_bp.route("/settings/logical_ids", methods=["POST"])
def add_logical_id():
    logical_name = request.form.get("logical_name")
    entry_type   = request.form.get("entry_type")
    video = request.form.get("video")
    audio = request.form.get("audio")
    data  = request.form.get("data")
    submitted_id = request.form.get("logical_id")

    cache = load_cache()
    senders = cache.get("senders") or cache.get("sources", [])
    receivers = cache.get("receivers", [])

    for s in senders:
        s["essence_type"] = (
            s.get("type")
            or s.get("essence")
            or get_resource_type(s)
        )
    for r in receivers:
        r["essence_type"] = (
            r.get("type")
            or r.get("essence")
            or get_resource_type(r)
        )

    def parse_label_sortkey(label):
        try:
            m = re.search(r"\[(\d+),(\d+),(\d+)\]", label)
            sfx = re.search(r"\](\d{2})", label)
            a, b, c = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (999, 999, 999)
            s = int(sfx.group(1)) if sfx else 0
            return (a, b, c, s, label.lower())
        except Exception:
            return (999, 999, 999, 999, label.lower())

    senders.sort(key=lambda x: (
        x.get("node_name") or "zzz",
        *parse_label_sortkey(x.get("label", ""))
    ))

    receivers.sort(key=lambda x: (
        x.get("node_name") or "zzz",
        *parse_label_sortkey(x.get("label", ""))
    ))

    logicals = load_logical_ids()
    logicals.setdefault(entry_type, {})

    used_ids = [v["id"] for v in logicals[entry_type].values() if "id" in v]

    if logical_name in logicals[entry_type]:
        return render_template(
            "logical.html",
            senders=senders,
            receivers=receivers,
            logical_ids=logicals,
            message=f"Logical group '{logical_name}' already exists for {entry_type}",
            message_type="error"
        )

    if submitted_id and int(submitted_id) in used_ids:
        return render_template(
            "logical.html",
            senders=senders,
            receivers=receivers,
            logical_ids=logicals,
            message=f"ID {submitted_id} already in use for {entry_type}",
            message_type="error"
        )

    group_id = next_contiguous_id(used_ids)

    logicals[entry_type][logical_name] = {"id": group_id}
    if video:
        logicals[entry_type][logical_name]["video"] = video
    if audio:
        logicals[entry_type][logical_name]["audio"] = audio
    if data:
        logicals[entry_type][logical_name]["data"] = data

    logicals[entry_type] = dict(sorted(
        logicals[entry_type].items(),
        key=lambda kv: kv[1].get("id", 9999)
    ))

    save_logical_ids(logicals)

    emulator = getattr(builtins, "videohub_emulator", None)
    loop = getattr(builtins, "main_event_loop", None)
    if emulator and loop:
        asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)

    return render_template(
        "logical.html",
        senders=senders,
        receivers=receivers,
        logical_ids=logicals,
        message=f"Added {entry_type} logical '{logical_name}' with ID={group_id} successfully.",
        message_type="success"
    )

@settings_bp.route('/settings/delete_logical_id', methods=['POST'])
def delete_logical_id():
    logical_name = request.form.get("logical_name")
    entry_type   = request.form.get("entry_type")

    logicals = load_logical_ids()

    if entry_type in logicals and logical_name in logicals[entry_type]:
        del logicals[entry_type][logical_name]
        save_logical_ids(logicals)

    emulator = getattr(builtins, "videohub_emulator", None)
    loop = getattr(builtins, "main_event_loop", None)
    if emulator and loop:
        asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)

    return redirect("/logical")

@settings_bp.route('/settings/update_logical_id', methods=['POST'])
def update_logical_id():
    original_name = request.form.get("original_name")
    logical_name  = request.form.get("logical_name")
    entry_type    = request.form.get("entry_type")
    video         = request.form.get("video") or None
    audio         = request.form.get("audio") or None
    data          = request.form.get("data")  or None
    logical_id    = int(request.form.get("logical_id", -1))

    logicals = load_logical_ids()

    for name, entry in logicals[entry_type].items():
        if name != original_name and entry.get("id") == logical_id:
            return f"Error: ID {logical_id} already in use for {entry_type}", 400

    if logical_name != original_name:
        logicals[entry_type][logical_name] = logicals[entry_type].pop(original_name)

    logicals[entry_type][logical_name]["id"]    = logical_id
    logicals[entry_type][logical_name]["video"] = video
    logicals[entry_type][logical_name]["audio"] = audio
    logicals[entry_type][logical_name]["data"]  = data

    save_logical_ids(logicals)

    emulator = getattr(builtins, "videohub_emulator", None)
    loop = getattr(builtins, "main_event_loop", None)
    if emulator and loop:
        asyncio.run_coroutine_threadsafe(emulator.reload_and_broadcast(), loop)

    return redirect("/logical")

def load_settings():
    default_settings = {
        "refresh_interval": 300,
        "patch_secondary": True,
        "enable_restapi": True,
        "enable_bmd_emulator": False,
        "enable_rosstalk_emulator": False
    }

    try:
        with open("settings.json", "r") as f:
            file_settings = json.load(f)
            return {**default_settings, **file_settings}
    except:
        return default_settings
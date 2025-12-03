# /services/cache.py
# by Arnaud Cresp - 2025

import os
import json
import threading
import time
from services.nmos_discovery import load_nodes, fetch_node_data, get_resource_type

CACHE_FILE = "data_cache.json"
SETTINGS_FILE = "settings.json"

_refresh_lock = threading.Lock()
_refresh_in_progress = False
_cache_ready_evt = threading.Event()

def wait_cache_ready(timeout=None):
    _cache_ready_evt.wait(timeout=timeout)

def read_cache():
    if not os.path.exists(CACHE_FILE):
        return {"receivers": [], "senders": [], "flows": [], "nodes": []}

    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)

        if (data.get("receivers") or data.get("senders")) and not _cache_ready_evt.is_set():
            _cache_ready_evt.set()

        return data

    except Exception as e:
        print(f"[ERROR] Failed to read cache: {e}")
        return {"receivers": [], "senders": [], "flows": [], "nodes": []}

def refresh_discovery(timeout=8):
    global _refresh_in_progress

    with _refresh_lock:
        if _refresh_in_progress:
            print("[INFO] Refresh already in progress, skipping.")
            return
        _refresh_in_progress = True

    try:
        print("[INFO] Refreshing NMOS discovery cache...")

        nodes = load_nodes()
        all_receivers = []
        all_senders = []
        all_flows = []
        all_nodes_info = []

        for node in nodes:
            node_name = node.get("name", "unknown")

            try:
                node_data = fetch_node_data(node, timeout=timeout)

                all_receivers.extend(node_data.get("receivers", []))
                all_senders.extend(node_data.get("sources", []))  # raw → senders
                all_flows.extend(node_data.get("flows", []))

                all_nodes_info.append({
                    "name": node_name,
                    "url": node.get("url"),
                    "ip": node_data.get("ip"),
                    "version": node_data.get("version")
                })

                print(f"[INFO] Node {node_name}: "
                      f"{len(node_data.get('receivers', []))} receivers, "
                      f"{len(node_data.get('sources', []))} senders, "
                      f"{len(node_data.get('flows', []))} flows")

            except Exception as e:
                print(f"[WARNING] Node {node_name} skipped ({e})")

        flows_index = {flow["id"]: flow for flow in all_flows}

        for r in all_receivers:
            t = get_resource_type(r, flows_index)
            r["type"] = t
            r["essence"] = t

        for s in all_senders:
            t = get_resource_type(s, flows_index)
            s["type"] = t
            s["essence"] = t

        cache = {
            "nodes": all_nodes_info,
            "receivers": all_receivers,
            "senders": all_senders,    # ✔ unique source of truth
            "flows": all_flows
        }

        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)

        if (all_receivers or all_senders) and not _cache_ready_evt.is_set():
            _cache_ready_evt.set()

        print(f"[INFO] Discovery cache updated with:")
        print(f"       - {len(all_nodes_info)} nodes")
        print(f"       - {len(all_receivers)} receivers")
        print(f"       - {len(all_senders)} senders")
        print(f"       - {len(all_flows)} flows")

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        with _refresh_lock:
            _refresh_in_progress = False

def get_refresh_interval():
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            val = int(settings.get("refresh_interval", 600))
            print(f"[DEBUG] Refresh interval: {val}s")
            return val
    except Exception as e:
        print(f"[ERROR] Failed to read refresh interval: {e}")
        return 600

def start_auto_refresh(kickoff=False):
    def loop():
        if kickoff:
            refresh_discovery(timeout=8)

        while True:
            interval = get_refresh_interval()
            print(f"[INFO] Auto-refresh will start in {interval} seconds.")
            time.sleep(interval)
            refresh_discovery(timeout=8)

    threading.Thread(target=loop, daemon=True).start()
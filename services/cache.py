# /services/cache.py
# by Arnaud Cresp - 2025

import os
import json
import threading
import time
from services.data_loader import load_nodes
from services.nmos_discovery import fetch_node_data, get_resource_type

CACHE_FILE = "data_cache.json"
SETTINGS_FILE = "settings.json"

_refresh_lock = threading.Lock()
_refresh_in_progress = False
_cache_ready_evt = threading.Event()

def wait_cache_ready(timeout=None):
    _cache_ready_evt.wait(timeout=timeout)

def read_cache():
    if not os.path.exists(CACHE_FILE):
        return {"receivers": [], "sources": []}
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            if (data.get("receivers") or data.get("sources")) and not _cache_ready_evt.is_set():
                _cache_ready_evt.set()
            return data
    except Exception as e:
        print(f"[ERROR] Failed to read cache: {e}")
        return {"receivers": [], "sources": []}

def refresh_discovery(timeout=8):
    global _refresh_in_progress

    with _refresh_lock:
        if _refresh_in_progress:
            print("[INFO] Refresh already in progress, skipping this one.")
            return
        _refresh_in_progress = True

    try:
        print("[INFO] Refreshing NMOS discovery cache...")
        nodes = load_nodes()
        all_receivers, all_sources = [], []

        for node in nodes:
            node_name = node.get("name", "unknown")
            try:
                node_data = fetch_node_data(node, timeout=timeout)

                for r in node_data.get("receivers", []):
                    r["ype"] = get_resource_type(r)
                for s in node_data.get("sources", []):
                    s["type"] = get_resource_type(s)

                all_receivers.extend(node_data.get("receivers", []))
                all_sources.extend(node_data.get("sources", []))
                print(f"[INFO] Node {node_name}: {len(node_data.get('receivers', []))} receivers, {len(node_data.get('sources', []))} sources")

            except Exception as e:
                print(f"[WARNING] Node {node_name} skipped ({e})")

        cache = {"receivers": all_receivers, "sources": all_sources}
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            if (all_receivers or all_sources) and not _cache_ready_evt.is_set():
                _cache_ready_evt.set()
        except Exception as e:
            print(f"[ERROR] Failed to write cache: {e}")

        print(f"[INFO] Discovery cache updated with {len(nodes)} nodes, {len(all_receivers)} receivers, {len(all_sources)} sources.")

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

    t = threading.Thread(target=loop, daemon=True)
    t.start()
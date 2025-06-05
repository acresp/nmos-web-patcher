import os
import json
import threading
import time
from services.data_loader import load_nodes
from services.nmos_discovery import fetch_node_data, get_resource_type

def refresh_discovery():
    print("[INFO] Refreshing NMOS discovery cache...")
    nodes = load_nodes()
    all_receivers = []
    all_sources = []

    for node in nodes:
        node_data = fetch_node_data(node)

        for r in node_data.get("receivers", []):
            r["type"] = get_resource_type(r)

        for s in node_data.get("sources", []):
            s["type"] = get_resource_type(s)

        all_receivers.extend(node_data.get("receivers", []))
        all_sources.extend(node_data.get("sources", []))

    cache = {
        "nodes": nodes,
        "receivers": all_receivers,
        "sources": all_sources
    }

    with open("data_cache.json", "w") as f:
        json.dump(cache, f, indent=2)

    print(f"[INFO] Discovery cache updated with {len(nodes)} nodes, {len(all_receivers)} receivers, {len(all_sources)} sources.")

def read_cache():
    if not os.path.exists("data_cache.json"):
        print("[WARNING] Cache file missing.")
        return {"nodes": [], "receivers": [], "sources": []}
    try:
        with open("data_cache.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read cache: {e}")
        return {"nodes": [], "receivers": [], "sources": []}

def get_refresh_interval():
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
            print(f"[DEBUG] Refresh interval loaded from settings: {settings.get('refresh_interval')}")
            return int(settings.get("refresh_interval", 600))
    except Exception as e:
        print(f"[ERROR] Failed to read refresh interval: {e}")
        return 600

def start_auto_refresh():
    def loop():
        while True:
            refresh_discovery()
            interval = get_refresh_interval() 
            print(f"[INFO] Next auto refresh in {interval} seconds.")
            time.sleep(interval)
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

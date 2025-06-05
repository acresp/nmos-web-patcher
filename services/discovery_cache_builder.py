import json
from services.nmos_discovery import fetch_node_data
from routes.settings import load_nodes

def refresh_discovery():
    print("[INFO] Refreshing NMOS discovery cache...")
    nodes = load_nodes()
    all_receivers = []
    all_sources = []

    for node in nodes:
        node_data = fetch_node_data(node)
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

import os
import json
import requests

NODES_FILE = 'nodes.json'

def load_nodes():
    if not os.path.exists(NODES_FILE):
        return []
    with open(NODES_FILE, 'r') as f:
        return json.load(f)

def save_nodes(nodes):
    with open(NODES_FILE, 'w') as f:
        json.dump(nodes, f, indent=4)

from services.nmos_discovery import fetch_node_data, get_resource_type

def load_receivers_and_sources(nodes):

    all_receivers = []
    all_senders = []

    for node in nodes:
        try:
            if not isinstance(node, dict):
                print(f"[WARNING] Skipping malformed node: {node}")
                continue

            name = node.get('label') or node.get('name') or "Unnamed"
            base_url = node.get('url')
            if not base_url:
                print(f"[WARNING] Node {name} has no 'url', skipping")
                continue

            base_url = base_url.rstrip('/')
            node_version = node.get('versions', {}).get('nmos', 'v1.3')

            def build_url(resource):
                if '/x-nmos' in base_url:
                    return f"{base_url}/node/{node_version}/{resource}"
                else:
                    return f"{base_url}/x-nmos/node/{node_version}/{resource}"

            # Fetch Receivers
            try:
                rcv_url = build_url('receivers')
                r = requests.get(rcv_url, timeout=2)
                r.raise_for_status()
                receivers = r.json()
                for rcv in receivers:
                    if isinstance(rcv, dict):
                        rcv['node_name'] = name
                        rcv['node_url'] = base_url
                        all_receivers.append(rcv)
            except Exception as e:
                print(f"[ERROR] Failed to fetch receivers from {name}: {e}")

            # Fetch Senders
            try:
                snd_url = build_url('senders')
                r = requests.get(snd_url, timeout=2)
                r.raise_for_status()
                senders = r.json()
                for snd in senders:
                    if isinstance(snd, dict):
                        snd['node_name'] = name
                        snd['node_url'] = base_url
                        all_senders.append(snd)
            except Exception as e:
                print(f"[ERROR] Failed to fetch senders from {name}: {e}")

        except Exception as e:
            print(f"[ERROR] General failure on node {name}: {e}")

    print(f"[DEBUG] Done loading. Found {len(all_receivers)} receivers and {len(all_senders)} sources")
    return all_receivers, all_senders

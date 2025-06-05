import requests
import concurrent.futures
from .nmos_discovery import fetch_node_data, get_resource_type

def load_receivers_and_sources(nodes):
    receivers, sources = [], []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_node_data, node): node for node in nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                data = future.result()
                for r in data.get('receivers', []):
                    r.update({
                        'node_name': node['name'],
                        'node_url': node['url'],
                        'versions': node.get('versions', {}),
                        'type': get_resource_type(r)
                    })
                    receivers.append(r)
                for s in data.get('sources', []):
                    s.update({
                        'node_name': node['name'],
                        'node_url': node['url'],
                        'versions': node.get('versions', {}),
                        'type': get_resource_type(s)
                    })
                    sources.append(s)
            except Exception as e:
                print(f"❌ Error fetching node {node['name']}: {e}")
    return receivers, sources

def change_source(nodes, receiver_id, sender_id):
    receivers, sources = load_receivers_and_sources(nodes)

    receiver = next((r for r in receivers if r['id'] == receiver_id), None)
    sender = next((s for s in sources if s['id'] == sender_id), None)
    if not sender:
        print(f"[WARN] Sender ID {sender_id} not found in loaded sources")


    if not receiver or not sender:
        return {"status": "error", "message": "Receiver or sender not found"}

    try:
        sdp_url = f"{sender['node_url']}connection/{sender['versions']['connection']}/single/senders/{sender_id}/transportfile/"
        sdp_data = requests.get(sdp_url, timeout=2).text

        patch_receiver = {
            "sender_id": sender_id,
            "master_enable": True,
            "transport_file": {
                "data": sdp_data,
                "type": "application/sdp"
            },
            "activation": {"mode": "activate_immediate"}
        }

        patch_url_receiver = f"{receiver['node_url']}connection/{receiver['versions']['connection']}/single/receivers/{receiver_id}/staged"
        r_patch = requests.patch(patch_url_receiver, json=patch_receiver, timeout=2)

        if r_patch.status_code != 200:
            return {"status": "error", "message": r_patch.text, "code": r_patch.status_code}

        patch_sender = {
            "activation": {"mode": "activate_immediate"},
            "master_enable": True
        }

        patch_url_sender = f"{sender['node_url']}connection/{sender['versions']['connection']}/single/senders/{sender_id}/staged"
        s_patch = requests.patch(patch_url_sender, json=patch_sender, timeout=2)

        if s_patch.status_code != 200:
            return {"status": "error", "message": s_patch.text, "code": s_patch.status_code}

        return {"status": "success", "message": "Source changed and sender activated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def disconnect_receiver(nodes, receiver_id):
    receivers, _ = load_receivers_and_sources(nodes)
    receiver = next((r for r in receivers if r['id'] == receiver_id), None)

    if not receiver:
        return {"status": "error", "message": "Receiver not found"}

    try:
        patch_data = {
            "sender_id": None,
            "master_enable": False,
            "activation": {"mode": "activate_immediate"}
        }

        patch_url = f"{receiver['node_url']}connection/{receiver['versions']['connection']}/single/receivers/{receiver_id}/staged"
        r_patch = requests.patch(patch_url, json=patch_data, timeout=2)

        if r_patch.status_code != 200:
            return {"status": "error", "message": r_patch.text, "code": r_patch.status_code}

        return {"status": "success", "message": "Disconnected successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

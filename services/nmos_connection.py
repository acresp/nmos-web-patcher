# /services/nmos_connection.py
# by Arnaud Cresp - 2025

import aiohttp
import time
import concurrent.futures
from services.nmos_discovery import fetch_node_data, get_resource_type
from routes.settings import load_settings
from utils.sdp_filter import remove_secondary_streams
from services.cache import read_cache

def load_receivers_and_sources(nodes):
    receivers, sources = [], []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_node_data, node): node for node in nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                data = future.result()
                for r in data.get("receivers", []):
                    r.update({
                        "node_name": node["name"],
                        "node_url": node["url"],
                        "versions": node.get("versions", {"connection": "v1.0"}),
                        "type": get_resource_type(r)
                    })
                    receivers.append(r)
                for s in data.get("sources", []):
                    s.update({
                        "node_name": node["name"],
                        "node_url": node["url"],
                        "versions": node.get("versions", {"connection": "v1.0"}),
                        "type": get_resource_type(s)
                    })
                    sources.append(s)
            except Exception as e:
                print(f"[ERROR] Error fetching node {node['name']}: {e}")
    return receivers, sources

def _join_url(base, path):
    if not base.endswith("/"):
        base += "/"
    return base + path

def _inject_metadata_from_nodes(receivers, sources, nodes):
    for r in receivers:
        if "node_url" not in r or not r.get("node_url"):
            node = next((n for n in nodes if n["name"] in r.get("device_label", "")), None)
            if not node:
                node = next((n for n in nodes if n["ip"] in r.get("device_label", "")), None)
            if node:
                r["node_url"] = node["url"]
                r["versions"] = node.get("versions", {"connection": "v1.0"})

    for s in sources:
        if "node_url" not in s or not s.get("node_url"):
            node = next((n for n in nodes if n["name"] in s.get("device_label", "")), None)
            if not node:
                node = next((n for n in nodes if n["ip"] in s.get("device_label", "")), None)
            if node:
                s["node_url"] = node["url"]
                s["versions"] = node.get("versions", {"connection": "v1.0"})

    return receivers, sources

async def change_source(nodes, receiver_id, sender_id, session=None, receivers=None, sources=None):
    t0_total = time.perf_counter()

    if receivers is None or sources is None:
        cache = read_cache()
        receivers = cache.get("receivers", [])
        sources = cache.get("sources", [])
        print(f"[CACHE] Using cached NMOS data: {len(receivers)} receivers, {len(sources)} sources")

    receivers, sources = _inject_metadata_from_nodes(receivers, sources, nodes)

    receiver = next((r for r in receivers if r.get("id") == receiver_id), None)
    sender = next((s for s in sources if s.get("id") == sender_id), None)

    if not sender or not receiver:
        return {"status": "error", "message": "Receiver or sender not found (check cache or logical mapping)"}

    own_session = False
    if session is None:
        session = aiohttp.ClientSession()
        own_session = True

    try:
        sdp_url = _join_url(sender["node_url"],
                            f"connection/{sender['versions']['connection']}/single/senders/{sender_id}/transportfile/")
        print(f"[TIMING] Fetching SDP from {sdp_url}")
        t0 = time.perf_counter()
        async with session.get(sdp_url, timeout=4) as resp:
            sdp_data = await resp.text()
        print(f"[TIMING] SDP fetched in {time.perf_counter() - t0:.3f}s")

        settings = load_settings()
        if not settings.get("patch_secondary", False):
            print("[INFO] Removing secondary streams from SDP")
            t0 = time.perf_counter()
            sdp_data = remove_secondary_streams(sdp_data)
            print(f"[TIMING] SDP filtering done in {time.perf_counter() - t0:.3f}s")

        patch_receiver = {
            "sender_id": sender_id,
            "master_enable": True,
            "transport_file": {"data": sdp_data, "type": "application/sdp"},
            "activation": {"mode": "activate_immediate"}
        }

        patch_url_receiver = _join_url(receiver["node_url"],
                                       f"connection/{receiver['versions']['connection']}/single/receivers/{receiver_id}/staged")
        print(f"[TIMING] Patching receiver {receiver_id}")
        t0 = time.perf_counter()
        async with session.patch(patch_url_receiver, json=patch_receiver, timeout=4) as r_patch:
            if r_patch.status != 200:
                msg = await r_patch.text()
                return {"status": "error", "message": msg, "code": r_patch.status}
        print(f"[TIMING] Receiver patched in {time.perf_counter() - t0:.3f}s")

        patch_sender = {"activation": {"mode": "activate_immediate"}, "master_enable": True}
        patch_url_sender = _join_url(sender["node_url"],
                                     f"connection/{sender['versions']['connection']}/single/senders/{sender_id}/staged")
        print(f"[TIMING] Activating sender {sender_id}")
        t0 = time.perf_counter()
        async with session.patch(patch_url_sender, json=patch_sender, timeout=4) as s_patch:
            if s_patch.status != 200:
                msg = await s_patch.text()
                return {"status": "error", "message": msg, "code": s_patch.status}
        print(f"[TIMING] Sender activated in {time.perf_counter() - t0:.3f}s")

        print(f"[OK] Patch complete in {time.perf_counter() - t0_total:.3f}s (metadata restored, no global refresh)")
        return {"status": "success", "message": "Source changed and sender activated successfully"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        if own_session and not session.closed:
            await session.close()

def disconnect_receiver(nodes, receiver_id, receivers=None):
    import requests

    if receivers is None:
        from services.cache import read_cache
        cache = read_cache()
        receivers = cache.get("receivers", [])
        print(f"[CACHE] Using cached NMOS data for disconnect: {len(receivers)} receivers")

    receivers, _ = _inject_metadata_from_nodes(receivers, [], nodes)

    receiver = next((r for r in receivers if r.get("id") == receiver_id), None)
    if not receiver:
        return {"status": "error", "message": f"Receiver {receiver_id} not found in cache"}

    # Payload IS-05 standard pour un disconnect propre (ajout du rtp_enable à false)
    patch_data = {
        "sender_id": None,
        "master_enable": False,
        "transport_params": [
            {"rtp_enabled": False}
        ],
        "activation": {"mode": "activate_immediate"}
    }

    patch_url = _join_url(
        receiver["node_url"],
        f"connection/{receiver['versions']['connection']}/single/receivers/{receiver_id}/staged"
    )

    print(f"[TIMING] Disconnecting receiver {receiver_id} via {patch_url}")
    try:
        r_patch = requests.patch(patch_url, json=patch_data, timeout=4)

        if r_patch.status_code in (200, 202):
            print(f"[NMOS DISCONNECT] Receiver {receiver_id} disconnected successfully (IS-05 staged).")
            return {"status": "success", "message": "Receiver disconnected successfully"}
        else:
            print(f"[NMOS DISCONNECT] Failed ({r_patch.status_code}): {r_patch.text}")
            return {"status": "error", "message": r_patch.text, "code": r_patch.status_code}

    except Exception as e:
        print(f"[NMOS DISCONNECT] Exception during disconnect: {e}")
        return {"status": "error", "message": str(e)}
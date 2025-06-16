# /services/nmos_connection.py
# by Arnaud Cresp - 2025

import aiohttp
import asyncio
import concurrent.futures
from .nmos_discovery import fetch_node_data, get_resource_type
from routes.settings import load_settings
from utils.sdp_filter import remove_secondary_streams

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
                print(f"Error fetching node {node['name']}: {e}")
    return receivers, sources

import aiohttp
from .nmos_discovery import fetch_node_data, get_resource_type
from routes.settings import load_settings
from utils.sdp_filter import remove_secondary_streams
from services.nmos_connection import load_receivers_and_sources

import aiohttp
from .nmos_discovery import fetch_node_data, get_resource_type
from routes.settings import load_settings
from utils.sdp_filter import remove_secondary_streams
from services.nmos_connection import load_receivers_and_sources

import aiohttp
import time
from .nmos_discovery import fetch_node_data, get_resource_type
from routes.settings import load_settings
from utils.sdp_filter import remove_secondary_streams
from services.nmos_connection import load_receivers_and_sources

async def change_source(nodes, receiver_id, sender_id, session=None, receivers=None, sources=None):
    if receivers is None or sources is None:
        print("[TIMING] Loading receivers and sources...")
        t0 = time.perf_counter()
        receivers, sources = load_receivers_and_sources(nodes)
        print(f"[TIMING] Discovery complete in {time.perf_counter() - t0:.3f}s")

    receiver = next((r for r in receivers if r['id'] == receiver_id), None)
    sender = next((s for s in sources if s['id'] == sender_id), None)

    if not sender or not receiver:
        return {"status": "error", "message": "Receiver or sender not found"}

    own_session = False
    if session is None:
        session = aiohttp.ClientSession()
        own_session = True

    try:
        sdp_url = f"{sender['node_url']}connection/{sender['versions']['connection']}/single/senders/{sender_id}/transportfile/"
        print(f"[TIMING] Fetching SDP from {sdp_url}")
        t0 = time.perf_counter()
        async with session.get(sdp_url, timeout=2) as resp:
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
            "transport_file": {
                "data": sdp_data,
                "type": "application/sdp"
            },
            "activation": {"mode": "activate_immediate"}
        }

        patch_url_receiver = f"{receiver['node_url']}connection/{receiver['versions']['connection']}/single/receivers/{receiver_id}/staged"
        print(f"[TIMING] Patching receiver {receiver_id}")
        t0 = time.perf_counter()
        async with session.patch(patch_url_receiver, json=patch_receiver, timeout=2) as r_patch:
            if r_patch.status != 200:
                return {
                    "status": "error",
                    "message": await r_patch.text(),
                    "code": r_patch.status
                }
        print(f"[TIMING] Receiver patched in {time.perf_counter() - t0:.3f}s")

        patch_sender = {
            "activation": {"mode": "activate_immediate"},
            "master_enable": True
        }

        patch_url_sender = f"{sender['node_url']}connection/{sender['versions']['connection']}/single/senders/{sender_id}/staged"
        print(f"[TIMING] Patching sender {sender_id}")
        t0 = time.perf_counter()
        async with session.patch(patch_url_sender, json=patch_sender, timeout=2) as s_patch:
            if s_patch.status != 200:
                return {
                    "status": "error",
                    "message": await s_patch.text(),
                    "code": s_patch.status
                }
        print(f"[TIMING] Sender patched in {time.perf_counter() - t0:.3f}s")

        return {"status": "success", "message": "Source changed and sender activated successfully"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        if own_session and not session.closed:
            await session.close()

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
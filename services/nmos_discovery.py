# /services/nmos_discovery.py
# by Arnaud Cresp - 2025

import requests
import json
import os
import time

def load_nodes():
    project_root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(project_root, "nodes.json")

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load nodes.json at {path}: {e}")
        return []

def safe_get_json(url, timeout=3, retries=2, delay=0.25):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    last_error = f"Invalid JSON (attempt {attempt})"
            else:
                last_error = f"HTTP {r.status_code}"
        except requests.exceptions.RequestException as e:
            last_error = str(e)
        time.sleep(delay)
    raise Exception(f"Failed to fetch {url} after {retries} tries ({last_error})")

def detect_nmos_and_connection_versions(node_url, timeout=3):
    import re, requests

    versions = {"nmos": None, "connection": None}
    node_url = node_url.rstrip("/")

    def parse_versions_from_response(resp_text):
        matches = re.findall(r'v\d+\.\d+', resp_text)
        if matches:
            cleaned = sorted(set(matches))
            return cleaned[-1]
        return None

    def get_highest_version(base, endpoint):
        try:
            url = f"{base}{endpoint}/"
            r = requests.get(url, timeout=timeout)

            if r.status_code != 200:
                return None

            try:
                data = r.json()
                if isinstance(data, list) and data:
                    versions_found = [
                        re.sub(r'[^v\d\.]', '', v)
                        for v in data if isinstance(v, str)
                    ]
                    valid = [v for v in versions_found if re.match(r'^v\d+\.\d+$', v)]
                    if valid:
                        return sorted(set(valid))[-1]
            except ValueError:
                pass

            return parse_versions_from_response(r.text)

        except Exception:
            return None
        
    node_ver = get_highest_version(node_url, "/x-nmos/node") \
            or get_highest_version(node_url, "/node")

    if node_ver:
        versions["nmos"] = node_ver

    conn_ver = get_highest_version(node_url, "/x-nmos/connection") \
            or get_highest_version(node_url, "/connection")

    if conn_ver:
        versions["connection"] = conn_ver

    if not versions["nmos"]:
        versions["nmos"] = "v1.0"

    if not versions["connection"]:
        versions["connection"] = "v1.0"

    return versions

def get_resource_type(resource, flows_index=None):
    res_type = (resource.get("type") or resource.get("essence") or "").lower()
    if "video" in res_type: return "video"
    if "audio" in res_type: return "audio"
    if "ancillary" in res_type or "metadata" in res_type: return "ancillary"

    flow_id = resource.get("flow_id")
    if flows_index and flow_id in flows_index:
        flow = flows_index[flow_id]
        fmt = flow.get("format", "").lower()
        mt = flow.get("media_type", "").lower()

        if "audio" in fmt or mt.startswith("audio/"): return "audio"
        if "data" in fmt and ("smpte291" in mt or "291" in mt): return "ancillary"
        if "video" in fmt or mt.startswith("video/"): return "video"

    label = resource.get("label", "").lower()
    if "video" in label: return "video"
    if "audio" in label: return "audio"
    if "metadata" in label or "ancillary" in label: return "ancillary"

    caps = resource.get("caps", {})
    if isinstance(caps, dict):
        mts = [m.lower() for m in caps.get("media_types", [])]
        if any(m.startswith("audio/") for m in mts): return "audio"
        if any("smpte291" in m or "291" in m for m in mts): return "ancillary"
        if any(m.startswith("video/") and "smpte291" not in m for m in mts): return "video"

    return "unknown"

def build_url(base, version, resource):
    base = base.rstrip('/')
    if base.endswith("/x-nmos") or "/x-nmos/" in base:
        return f"{base}/node/{version}/{resource}/"
    elif base.endswith("/node") or "/node/" in base:
        return f"{base}/{version}/{resource}/"
    else:
        return f"{base}/x-nmos/node/{version}/{resource}/"

def fetch_node_data(node, timeout=3):
    node_url = node['url'].rstrip('/')
    versions = node.get('versions') or detect_nmos_and_connection_versions(node_url, timeout=timeout)
    nmos_version = versions.get('nmos', 'v1.3')

    data = {
        'label': node.get('label', node.get('name', node_url)),
        'ip': node.get('ip', node_url),
        'version': nmos_version,
        'receivers': [],
        'senders': [],
        'flows': []
    }

    # Receivers
    try:
        rcv_url = build_url(node_url, nmos_version, 'receivers')
        rcv_json = safe_get_json(rcv_url, timeout=timeout)
        if isinstance(rcv_json, list):
            for item in rcv_json:
                item.update({
                    'node_name': node['name'],
                    'node_url': node_url,
                    'versions': versions
                })
                data['receivers'].append(item)
    except Exception as e:
        print(f"[WARNING] Node {node['name']} receivers skipped: {e}")

    # Senders
    try:
        snd_url = build_url(node_url, nmos_version, 'senders')
        snd_json = safe_get_json(snd_url, timeout=timeout)
        if isinstance(snd_json, list):
            for item in snd_json:
                item.update({
                    'node_name': node['name'],
                    'node_url': node_url,
                    'versions': versions
                })
                data['senders'].append(item)
    except Exception as e:
        print(f"[WARNING] Node {node['name']} senders skipped: {e}")

    # FLOWS
    try:
        flow_url = build_url(node_url, nmos_version, 'flows')
        flow_json = safe_get_json(flow_url, timeout=timeout)
        if isinstance(flow_json, list):
            for f in flow_json:
                data['flows'].append(f)
    except Exception as e:
        print(f"[WARNING] Node {node['name']} flows skipped: {e}")

    return data
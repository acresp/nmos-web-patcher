# /services/nmos_discovery.py
# by Arnaud Cresp - 2025

import requests
import json
import os
import time

def load_nodes():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'nodes.json')
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load nodes.json: {e}")
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
            # JSON case (expected NMOS response: ["v1.0", "v1.1", "v1.2", "v1.3"])
            try:
                data = r.json()
                if isinstance(data, list) and data:
                    versions_found = [
                        re.sub(r'[^v\d\.]', '', v).strip()
                        for v in data if isinstance(v, str)
                    ]
                    valid = [v for v in versions_found if re.match(r'^v\d+\.\d+$', v)]
                    if valid:
                        return sorted(set(valid))[-1]
            except ValueError:
                pass  # not JSON, continue to HTML parsing
            # HTML fallback (e.g. some devices return a directory listing)
            return parse_versions_from_response(r.text)
        except Exception as e:
            print(f"[DEBUG] Failed to query {endpoint}: {e}")
            return None
        
    # Detect IS-04 (Node)
    node_ver = get_highest_version(node_url, "/x-nmos/node") or get_highest_version(node_url, "/node")
    if node_ver:
        versions["nmos"] = node_ver

    # Detect IS-05 (Connection)
    conn_ver = get_highest_version(node_url, "/x-nmos/connection") or get_highest_version(node_url, "/connection")
    if conn_ver:
        versions["connection"] = conn_ver

    # Safety defaults
    if not versions["nmos"]:
        versions["nmos"] = "v1.0"
    if not versions["connection"]:
        versions["connection"] = "v1.0"

    return versions

def get_resource_type(resource):
    """Déduit le type d’une ressource NMOS (video/audio/ancillary)."""
    if not isinstance(resource, dict):
        return "invalid"

    fmt = str(resource.get('format', '')).lower()
    label = str(resource.get('label', '')).lower()
    description = str(resource.get('description', '')).lower()

    caps = resource.get('caps', {})
    media_types = []
    if isinstance(caps, dict):
        mt = caps.get('media_types')
        if isinstance(mt, list):
            media_types = [m.lower() for m in mt if isinstance(m, str)]

    clues = " ".join([fmt] + media_types + [label, description])

    if "audio" in clues:
        return "audio"
    if "smpte291" in clues or "anc" in clues or "metadata" in clues or "data" in clues:
        return "ancillary"
    if "video/raw" in clues or ("video" in clues and "smpte291" not in clues):
        return "video"

    if any(x in label for x in ["aud", "aes"]) or "audio" in description:
        return "audio"
    if any(x in label for x in ["anc", "data"]) or "anc" in description:
        return "ancillary"
    if any(x in label for x in ["vid", "pgm", "cam", "tx", "rx"]) or "video" in description:
        return "video"

    return "unknown"

def build_url(base, version, resource):
    """Construit une URL NMOS correcte."""
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
        'sources': []
    }

    try:
        rcv_url = build_url(node_url, nmos_version, 'receivers')
        rcv_json = safe_get_json(rcv_url, timeout=timeout)
        if isinstance(rcv_json, list):
            for item in rcv_json:
                if isinstance(item, dict):
                    item.update({
                        'node_name': node['name'],
                        'node_url': node_url,
                        'versions': versions
                    })
                    data['receivers'].append(item)
        else:
            print(f"[WARNING] Unexpected receivers format from {node['name']}: {type(rcv_json)}")
    except Exception as e:
        print(f"[WARNING] Node {node['name']} receivers skipped: {e}")

    try:
        snd_url = build_url(node_url, nmos_version, 'senders')
        snd_json = safe_get_json(snd_url, timeout=timeout)
        if isinstance(snd_json, list):
            for item in snd_json:
                if isinstance(item, dict):
                    item.update({
                        'node_name': node['name'],
                        'node_url': node_url,
                        'versions': versions
                    })
                    data['sources'].append(item)
        else:
            print(f"[WARNING] Unexpected senders format from {node['name']}: {type(snd_json)}")
    except Exception as e:
        print(f"[WARNING] Node {node['name']} senders skipped: {e}")

    return data
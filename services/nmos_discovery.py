import requests

def detect_nmos_and_connection_versions(node_url):
    versions = {
        "nmos": None,
        "connection": None
    }

    for version in reversed(["v1.0", "v1.1", "v1.2", "v1.3"]):
        try:
            url = f"{node_url}node/{version}/sources/"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and any("id" in s for s in data if isinstance(s, dict)):
                    versions["nmos"] = version
                    break
        except Exception:
            continue

    for version in reversed(["v1.0", "v1.1", "v1.2", "v1.3"]):
        try:
            url = f"{node_url}connection/{version}/single/receivers/"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and (
                    any(isinstance(d, dict) and "id" in d for d in data) or
                    all(isinstance(d, str) and len(d.strip("/")) >= 30 for d in data)
                ):
                    versions["connection"] = version
                    break
        except Exception:
            continue

    return versions

def get_resource_type(resource):
    if not isinstance(resource, dict):
        return "invalid"

    format = resource.get('format', '')
    label = resource.get('label', '').lower()
    description = resource.get('description', '').lower()
    tags = resource.get('tags', {})

    if "urn:x-nmos:format:video" in format:
        return "video"
    if "urn:x-nmos:format:audio" in format:
        return "audio"
    if "urn:x-nmos:format:data" in format:
        return "ancillary"
    if "video" in label or "vid" in label or "vision" in label:
        return "video"
    if "audio" in label or "aud" in label:
        return "audio"
    if "anc" in label:
        return "ancillary"
    if "video" in description:
        return "video"
    if "audio" in description:
        return "audio"
    if any("video" in tag.lower() for tag_list in tags.values() for tag in tag_list):
        return "video"

    return "unknown"

def fetch_node_data(node):
    node_url = node['url'].rstrip('/')
    nmos_version = node.get('versions', {}).get('nmos', 'v1.3')

    data = {
        'label': node.get('label', node.get('name', node_url)),
        'ip': node.get('ip', node_url),
        'version': nmos_version,
        'receivers': [],
        'sources': []
    }

    def build_url(base, version, resource):
        if '/x-nmos' in base:
            return f"{base}/node/{version}/{resource}/"
        else:
            return f"{base}/x-nmos/node/{version}/{resource}/"

    try:
        rcv_url = build_url(node_url, nmos_version, 'receivers')
        r = requests.get(rcv_url, timeout=3)
        r.raise_for_status()
        rcv_json = r.json()
        if isinstance(rcv_json, list):
            receivers = [d for d in rcv_json if isinstance(d, dict)]
            for item in receivers:
                item['node_name'] = node['name']
            data['receivers'] = receivers
        else:
            print(f"[WARNING] Unexpected receivers format from {node['name']}: {type(rcv_json)}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch receivers from {node['name']}: {e}")

    try:
        snd_url = build_url(node_url, nmos_version, 'senders')
        r = requests.get(snd_url, timeout=3)
        r.raise_for_status()
        snd_json = r.json()
        if isinstance(snd_json, list):
            senders = [d for d in snd_json if isinstance(d, dict)]
            for item in senders:
                item['node_name'] = node['name']
            data['sources'] = senders
        else:
            print(f"[WARNING] Unexpected senders format from {node['name']}: {type(snd_json)}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch senders from {node['name']}: {e}")

    return data

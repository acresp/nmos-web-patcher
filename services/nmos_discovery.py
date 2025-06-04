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
    data = {'receivers': [], 'sources': []}

    try:
        rcv_url = f"{node_url}/node/{nmos_version}/receivers/"
        r = requests.get(rcv_url, timeout=3)
        if r.status_code == 200:
            data['receivers'] = [d for d in r.json() if isinstance(d, dict)]
    except Exception as e:
        print(f"❌ Failed to fetch receivers from {node['name']}: {e}")

    try:
        snd_url = f"{node_url}/node/{nmos_version}/senders/"
        r = requests.get(snd_url, timeout=3)
        if r.status_code == 200:
            data['sources'] = [d for d in r.json() if isinstance(d, dict)]
    except Exception as e:
        print(f"❌ Failed to fetch sources from {node['name']}: {e}")

    return data

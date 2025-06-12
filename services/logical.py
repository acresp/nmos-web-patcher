# /services/logical.py
# by Arnaud Cresp - 2025

import json
from pathlib import Path

LOGICAL_FILE = Path("data_logical.json")

def load_logical_ids():
    if LOGICAL_FILE.exists():
        with open(LOGICAL_FILE, "r") as f:
            return json.load(f)
    return {"sources": {}, "receivers": {}}

def save_logical_ids(data):
    with open(LOGICAL_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_logical_pair(src_id, dest_id):
    logical = load_logical_ids()
    sources = logical.get("sources", {})
    receivers = logical.get("receivers", {})

    src = next((v for v in sources.values() if str(v.get("id")) == str(src_id)), None)
    dest = next((v for v in receivers.values() if str(v.get("id")) == str(dest_id)), None)

    return src, dest

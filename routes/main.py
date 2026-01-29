# /routes/main.py
# by Arnaud Cresp - 2025

from flask import Blueprint, render_template
from collections import defaultdict
from services.cache import read_cache
from services.data_loader import load_nodes
from services.nmos_discovery import get_resource_type
import re

main_bp = Blueprint('main', __name__)

def extract_sort_key(item):
    label = item.get("label", "").lower()
    tags = item.get("tags", {})

    triplet_str = next(
        (t for k, v in tags.items() for t in v if "grouphint" in k and "[" in t),
        ""
    )

    if not triplet_str:
        triplet_str = label

    match = re.search(r"\[(\d+),\s*(\d+),\s*(\d+)]", triplet_str)
    if match:
        return tuple(map(int, match.groups()))

    match2 = re.search(r"\[(\d+)]", label)
    if match2:
        return (999, 999, int(match2.group(1)))

    return (999, 999, 999, label)

def group_by_node_and_type(items):
    grouped = defaultdict(lambda: defaultdict(list))
    for item in items:
        node_name = item.get("node_name", "Unknown Node")
        essence_type = (
            item.get("type")
            or item.get("essence")
            or item.get("essence_type")
            or get_resource_type(item)
        )
        grouped[node_name][essence_type].append(item)
    return grouped

@main_bp.route('/')
def index():
    cache = read_cache()

    receivers = cache.get('receivers', [])
    senders   = cache.get('senders', [])

    grouped_receivers = group_by_node_and_type(sorted(receivers, key=extract_sort_key))
    grouped_senders   = group_by_node_and_type(sorted(senders,   key=extract_sort_key))

    nodes = load_nodes()

    return render_template(
    'index.html',
    grouped_receivers=grouped_receivers,
    grouped_senders=grouped_senders,
    receivers=receivers,
    senders=senders,
    nodes=nodes,
    node_count=len(nodes),
    receiver_count=len(receivers),
    sender_count=len(senders)
)
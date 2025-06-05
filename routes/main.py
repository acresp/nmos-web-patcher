from flask import Blueprint, render_template
from services.cache import read_cache
import re

main_bp = Blueprint('main', __name__)

import re

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

@main_bp.route('/')
def index():
    cache = read_cache()

    receivers = cache['receivers']
    sources = cache['sources']

    receivers = sorted(cache['receivers'], key=extract_sort_key)
    sources = sorted(cache['sources'], key=extract_sort_key)


    return render_template(
        'index.html',
        receivers=receivers,
        sources=sources,
        nodes=cache['nodes'],
        node_count=len(cache['nodes']),
        receiver_count=len(receivers),
        source_count=len(sources),
        selected_receiver_id=None,
        selected_source_id=None
    )

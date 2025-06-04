from flask import Blueprint, request, jsonify
from services.data_loader import load_nodes
from services.nmos_connection import change_source, disconnect_receiver

api_bp = Blueprint('api', __name__)

@api_bp.route('/change_source', methods=['POST'])
def api_change_source():
    data = request.json
    receiver_id = data.get('receiver_id')
    sender_id = data.get('sender_id')

    if not receiver_id or not sender_id:
        return jsonify({"status": "error", "message": "Missing receiver or sender ID"}), 400

    nodes = load_nodes()
    result = change_source(nodes, receiver_id, sender_id)
    return jsonify(result), (200 if result["status"] == "success" else result.get("code", 500))

@api_bp.route('/disconnect_receiver', methods=['POST'])
def api_disconnect_receiver():
    data = request.json
    receiver_id = data.get('receiver_id')

    if not receiver_id:
        return jsonify({"status": "error", "message": "Missing receiver ID"}), 400

    nodes = load_nodes()
    result = disconnect_receiver(nodes, receiver_id)
    return jsonify(result), (200 if result["status"] == "success" else result.get("code", 500))

@api_bp.route('/get_current_sender/<receiver_id>')
def get_current_sender(receiver_id):
    from services.data_loader import load_receivers_and_sources
    import requests

    nodes = load_nodes()
    receivers, sources = load_receivers_and_sources(nodes)

    sources = [s for s in sources if isinstance(s, dict)]  # Sanity check

    receiver = next((r for r in receivers if r['id'] == receiver_id), None)
    if not receiver:
        print(f"[WARNING] Receiver with ID {receiver_id} not found")
        return jsonify({"status": "error", "message": "Receiver not found"})

    node_url = receiver['node_url']
    version = receiver.get('versions', {}).get('connection', 'v1.1')

    try:
        url = f"{node_url}/connection/{version}/single/receivers/{receiver_id}/active/"
        r = requests.get(url, timeout=2)

        if r.status_code == 200:
            data = r.json()
            sender_id = data.get("sender_id")

            if not sender_id:
                print(f"[INFO] Receiver {receiver_id} is not connected to any sender")
                return jsonify({
                    "status": "success",
                    "current_sender_label": "None",
                    "current_sender_node": "Unknown"
                })

            sender = next((s for s in sources if s.get('id') == sender_id), None)
            if sender:
                return jsonify({
                    "status": "success",
                    "current_sender_label": sender.get("label", "Unknown"),
                    "current_sender_node": sender.get("node_name", "Unknown")
                })
            else:
                print(f"[WARNING] Sender ID {sender_id} not found in known sources")
                return jsonify({
                    "status": "success",
                    "current_sender_label": "Unknown",
                    "current_sender_node": "Unknown"
                })
        else:
            print(f"[ERROR] Failed to fetch active sender. Status code: {r.status_code}")
            return jsonify({"status": "error", "message": "Could not fetch active sender"}), 404

    except Exception as e:
        print(f"[EXCEPTION] Error in get_current_sender: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
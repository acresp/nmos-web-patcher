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

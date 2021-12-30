from datetime import datetime
from flask import Flask, jsonify, request
from uuid import uuid4

app = Flask(__name__)

queue = {str(uuid4()): dict(build_id=None, steps=[]) for _ in range(10)}
builds = {}

def _error(msg, status=400):
    return jsonify(dict(error=msg)), status

def _timestamp():
    return f'{datetime.utcnow().isoformat()}Z'

@app.route('/queue', methods=['GET'])
def queue_route():
    queue_list = [{'id': key, **value} for key, value in queue.items() if not value.get('build_id')]

    return jsonify(queue_list)

@app.route('/queue/<queue_id>/init', methods=['POST'])
def queue_item_init_route(queue_id):
    if queue_id not in queue:
        return _error(f'Queue item {queue_id} not in queue.', 404)

    node = (request.get_json() or {}).get('node')
    if not node:
        return _error('node must be defined')

    build_id = str(uuid4())
    queue[queue_id]['build_id'] = build_id
    builds[build_id] = dict(node=node, started=_timestamp(), finished=None)

    return jsonify(dict(build_id=build_id)), 201

@app.route('/builds/<build_id>', methods=['GET'])
def builds_item_route(build_id):
    if build_id not in builds:
        return _error(f'Build {build_id} not found.', 404)

    return jsonify({'id': build_id, **builds[build_id]})

@app.route('/builds/<build_id>/complete', methods=['POST'])
def builds_item_complete_route(build_id):
    if build_id not in builds:
        return _error(f'Build {build_id} not found.', 404)

    builds[build_id]['finished'] = _timestamp()
    return '', 204

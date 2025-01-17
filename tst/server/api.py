from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from os import getenv
from random import uniform
from time import sleep
from uuid import uuid4

from ciou.time import timestamp

app = Flask(__name__)

queue = {str(uuid4()): dict(build_id=None, steps=[]) for _ in range(10)}
builds = {}

def start():
    app.run()

def simulate_delay():
    if getenv('SIMULATE_DELAY'):
        sleep(uniform(1,5))

def _error(msg, status=400):
    return jsonify(dict(error=msg)), status

@app.route("/")
@app.route("/<path:path>")
def static_route(path=None):
    simulate_delay()
    return send_from_directory('static', path or 'index.html')

@app.route('/queue', methods=['GET'])
def queue_route():
    simulate_delay()
    queue_list = [{'id': key, **value} for key, value in queue.items() if not value.get('build_id')]

    return jsonify(queue_list)

@app.route('/queue/<queue_id>/init', methods=['POST'])
def queue_item_init_route(queue_id):
    simulate_delay()
    if queue_id not in queue:
        return _error(f'Queue item {queue_id} not in queue.', 404)

    node = (request.get_json() or {}).get('node')
    if not node:
        return _error('node must be defined')

    build_id = str(uuid4())
    queue[queue_id]['build_id'] = build_id
    builds[build_id] = dict(node=node, started=timestamp(), finished=None)

    return jsonify(dict(build_id=build_id)), 201

@app.route('/builds/<build_id>', methods=['GET'])
def builds_item_route(build_id):
    simulate_delay()
    if build_id not in builds:
        return _error(f'Build {build_id} not found.', 404)

    return jsonify({'id': build_id, **builds[build_id]})

@app.route('/builds/<build_id>/complete', methods=['POST'])
def builds_item_complete_route(build_id):
    simulate_delay()
    if build_id not in builds:
        return _error(f'Build {build_id} not found.', 404)

    builds[build_id]['finished'] = timestamp()
    return '', 204

numbers = dict(count=0)
@app.route('/numbers/count', methods=['GET'])
def numbers_count_route():
    simulate_delay()
    numbers['count'] += 1
    return jsonify(dict(count=numbers.get('count')))

words = list()
@app.route('/words', methods=['DELETE', 'GET', 'POST'])
def words_route():
    simulate_delay()
    if request.method == 'DELETE':
        words.clear()
        return '', 204
    if request.method == 'POST':
        word = (request.get_json() or {}).get('word')
        if not word:
            return _error('word must be defined')

        words.append(word)
        return '', 204
    return jsonify(words)

from flask import Flask, jsonify
import json
import os

app = Flask(__name__)
@app.route('/')
def get_status():
with open('status.json', 'r') as f:
return jsonify(json.load(f))

app.run(host='0.0.0.0', port=5000)

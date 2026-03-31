#!/usr/bin/env python3
\"\"\"Simple Flask server for fixed K8s dashboard - no extras needed\"\"\"

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
# Import fixed k8s blueprint
from blueprints.k8s_routes import k8s_bp

# Kubernetes env setup
os.environ['KUBECONFIG'] = os.path.expanduser('~/.kube/config')
os.environ['KUBECTL_PATH'] = r'C:\Program Files\Docker\Docker\resources\bin\kubectl.exe'
print(f\"KUBECONFIG: {os.environ['KUBECONFIG']}\")
print(f\"KUBECTL_PATH: {os.environ['KUBECTL_PATH']}\")

app = Flask(__name__, static_folder='../ui', static_url_path='')
CORS(app)

app.register_blueprint(k8s_bp, url_prefix='/api')

@app.route('/')
def index():
    return send_from_directory('../ui', 'index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'k8s': 'fixed'})

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../ui', path)

if __name__ == '__main__':
    print(\"🚀 Starting simple DevOps dashboard on http://127.0.0.1:5000\")
    print(\"📊 UI: http://127.0.0.1:5000\")
    print(\"🔍 Test API: curl http://127.0.0.1:5000/api/k8s/pods\")
    app.run(host='0.0.0.0', port=5000, debug=False)


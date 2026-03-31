#!/usr/bin/env python3
# Main Production App - Blueprints + SocketIO
# Based on app_fixed.py + new structure

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, g, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Blueprints
from blueprints import auth_bp, k8s_bp, jenkins_bp, metrics_bp, users_bp

# Config from env (from app_fixed.py)
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    DATABASE_URL = os.getenv('DATABASE_URL', 'users.db')
    JENKINS_URL = os.getenv('JENKINS_URL', 'http://localhost:8080')
    K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'default')

# Kubernetes environment setup for Windows/Minikube
import subprocess
os.environ['KUBECONFIG'] = os.path.expanduser('~/.kube/config')
os.environ['KUBECTL_PATH'] = r'C:\Program Files\Docker\Docker\resources\bin\kubectl.exe'
print(f"KUBECONFIG set to: {os.environ['KUBECONFIG']}")
print(f"KUBECTL_PATH set to: {os.environ['KUBECTL_PATH']}")

config = Config()
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')  # Real-time layer

# DB (extend with SQLAlchemy later)
def get_db_connection():
    import sqlite3
    conn = sqlite3.connect(config.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

# JWT decorators from app_fixed.py
from functools import wraps
def jwt_required_decorator(f):
    from flask_jwt_extended import jwt_required, get_jwt_identity
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        g.current_user = get_jwt_identity()
        return f(*args, **kwargs)
    return decorated

# Global bcrypt (lazy import)
bcrypt = None
def get_bcrypt():
    global bcrypt
    if bcrypt is None:
        import bcrypt
    return bcrypt

# Register all Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(k8s_bp)
app.register_blueprint(jenkins_bp)
app.register_blueprint(metrics_bp)
app.register_blueprint(users_bp)

# SocketIO Events - Real-time
@socketio.on('connect')
def handle_connect():
    emit('status', {'data': 'Connected to DevOps Platform WebSocket'})

@socketio.on('join_logs')
def on_join_logs(data):
    pod = data['pod']
    join_room(pod)
    emit('status', {'msg': f'Joined logs for {pod}'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Health (from fixed)
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '3.0.0'})

@app.route('/')
def index():
    return send_from_directory('frontend/build', 'index.html')  # After React build

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


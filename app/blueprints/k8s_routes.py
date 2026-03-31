from flask import Blueprint, jsonify, request
from ..app import jwt_required_decorator, config as app_config
import os
import subprocess
import json
from datetime import datetime

k8s_bp = Blueprint('k8s', __name__, url_prefix='/api/k8s')

KUBECTL_PATH = os.environ.get('KUBECTL_PATH', r'C:\Program Files\Docker\Docker\resources\bin\kubectl.exe')

def safe_kubectl(cmd):
    """Execute kubectl with Windows path, timeout, error handling"""
    full_cmd = [KUBECTL_PATH] + cmd
    try:
        env = os.environ.copy()
        env['KUBECONFIG'] = os.path.expanduser('~/.kube/config')
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=20,
            env=env
        )
        print(f"KUBECTL CMD: {' '.join(full_cmd)}")
        print("STDOUT:", result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
        print("STDERR:", result.stderr)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr or "Command failed with no output"}
    except subprocess.TimeoutExpired:
        return {"error": "kubectl timeout (20s)"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from kubectl"}
    except Exception as e:
        return {"error": str(e)}

@k8s_bp.route('/health')
@jwt_required_decorator
def health():
    # Extracted from app_fixed.py subprocess version - now native client
    try:
        nodes = v1.list_node()
        ready_count = sum(1 for node in nodes.items if any(c.status == 'True' and c.type == 'Ready' for c in node.status.conditions))
        return jsonify({
            'status': 'UP' if ready_count == len(nodes.items) else 'DEGRADED',
            'nodes': [{'name': n.metadata.name, 'status': 'Ready'} for n in nodes.items[:5]]  # Limit
        })
    except Exception as e:
        return jsonify({'status': 'DOWN', 'error': str(e)})

@k8s_bp.route('/pods')
@jwt_required_decorator
def get_pods():
    data = safe_kubectl(["get", "pods", "-A", "-o", "json"])
    if "error" in data:
        return jsonify([data])
    if "items" not in data:
        return jsonify([])
    
    pods = []
    for item in data["items"]:
        metadata = item["metadata"]
        spec = item["spec"]
        status = item["status"] or {}
        pod_ip = status.get("podIP", "N/A")
        pod_status = status.get("phase", "Unknown")
        node_name = spec.get("nodeName", "N/A")
        
        pods.append({
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "status": pod_status,
            "node": node_name,
            "ip": pod_ip
        })
    return jsonify(pods)

@k8s_bp.route('/deployments')
@jwt_required_decorator
def get_deployments():
    data = safe_kubectl(["get", "deployments", "-A", "-o", "json"])
    if "error" in data:
        return jsonify([data])
    if "items" not in data:
        return jsonify([])
    
    deployments = []
    for item in data["items"]:
        metadata = item["metadata"]
        spec = item["spec"]
        replicas = spec.get("replicas", 0)
        
        deployments.append({
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "replicas": replicas
        })
    return jsonify(deployments)

@k8s_bp.route('/logs')
@jwt_required_decorator
def get_logs():
    pod = request.args.get('pod')
    namespace = request.args.get('namespace', 'default')
    if not pod:
        return jsonify({"error": "pod parameter required"}), 400
    
    cmd = ["logs", pod, "-n", namespace, "--tail=100"]
    result = subprocess.run(
        [KUBECTL_PATH] + cmd,
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, 'KUBECONFIG': os.path.expanduser('~/.kube/config')}
    )
    print(f"LOGS CMD: kubectl {' '.join(cmd)}")
    print("LOGS STDOUT length:", len(result.stdout))
    print("LOGS STDERR:", result.stderr)
    
    if result.returncode == 0:
        return jsonify({
            "pod": pod,
            "namespace": namespace,
            "logs": result.stdout
        })
    else:
        return jsonify({
            "error": result.stderr or "Failed to get logs"
        })

@k8s_bp.route('/action', methods=['POST'])
@jwt_required_decorator
def action():
    # Keep existing action for compatibility
    return jsonify({'success': True, 'message': 'Action endpoint ready (subprocess coming soon)'})


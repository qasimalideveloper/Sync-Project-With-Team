"""
Simple File Sync Server - ZIP Archive Based
Stores frontend and backend folders as ZIP archives
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import time
import threading
import io

app = Flask(__name__)
CORS(app, origins="*")
    
# Storage for ZIP archives
frontend_archive = None  # bytes
backend_archive = None  # bytes
frontend_timestamp = None
backend_timestamp = None
frontend_uploaded_by = None
backend_uploaded_by = None

lock = threading.Lock()

# Track connected clients (one at a time)
connected_clients = {}  # {client_id: {"last_seen": float, "connected_at": float}}
client_lock = threading.Lock()
HEARTBEAT_TIMEOUT = 30  # 30 seconds timeout

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "online", "timestamp": time.time()}), 200

@app.route('/register', methods=['POST'])
def register_client():
    """Register a client - check if others are active"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        client_id = data.get('client_id', '')
        
        if not client_id or str(client_id).strip() == '':
            print(f"[ERROR] Invalid client_id: {repr(client_id)}")
            return jsonify({"error": "client_id required and cannot be empty"}), 400
        
        current_time = time.time()
        
        with client_lock:
            # Clean up stale clients
            stale_clients = [
                cid for cid, info in connected_clients.items()
                if (current_time - info["last_seen"]) >= HEARTBEAT_TIMEOUT
            ]
            for cid in stale_clients:
                del connected_clients[cid]
            
            # Check if other clients are active (excluding this one)
            other_clients = [
                {"client_id": cid, "connected_at": info["connected_at"]}
                for cid, info in connected_clients.items()
                if cid != client_id and (current_time - info["last_seen"]) < HEARTBEAT_TIMEOUT
            ]
            
            # Register or update this client
            if client_id not in connected_clients:
                connected_clients[client_id] = {
                    "connected_at": current_time,
                    "last_seen": current_time
                }
                print(f"[CLIENT CONNECTED] {client_id}")
            else:
                connected_clients[client_id]["last_seen"] = current_time
            
            return jsonify({
                "status": "registered",
                "client_id": client_id,
                "other_clients_active": len(other_clients) > 0,
                "other_clients": other_clients,
                "timestamp": current_time
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/unregister', methods=['POST'])
def unregister_client():
    """Unregister a client"""
    try:
        data = request.get_json()
        client_id = data.get('client_id', 'unknown')
        
        with client_lock:
            if client_id in connected_clients:
                del connected_clients[client_id]
                print(f"[CLIENT DISCONNECTED] {client_id}")
                return jsonify({"status": "unregistered", "client_id": client_id}), 200
            else:
                return jsonify({"status": "not found", "client_id": client_id}), 404
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_active', methods=['GET'])
def check_active_clients():
    """Check if any other clients are currently active"""
    try:
        client_id = request.args.get('client_id', 'unknown')
        current_time = time.time()
        
        with client_lock:
            # Clean up stale clients
            stale_clients = [
                cid for cid, info in connected_clients.items()
                if (current_time - info["last_seen"]) >= HEARTBEAT_TIMEOUT
            ]
            for cid in stale_clients:
                del connected_clients[cid]
            
            # Get active clients (excluding the requesting client)
            active_clients = [
                {"client_id": cid, "connected_at": info["connected_at"]}
                for cid, info in connected_clients.items()
                if cid != client_id and (current_time - info["last_seen"]) < HEARTBEAT_TIMEOUT
            ]
            
            return jsonify({
                "other_clients_active": len(active_clients) > 0,
                "active_clients": active_clients,
                "total_connected": len(connected_clients),
                "timestamp": current_time
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload/frontend', methods=['POST'])
def upload_frontend():
    """Upload frontend folder as ZIP"""
    try:
        client_id = request.form.get('client_id', 'unknown')
        
        if 'archive' not in request.files:
            return jsonify({"error": "No archive file provided"}), 400
        
        archive_file = request.files['archive']
        archive_data = archive_file.read()
        
        if len(archive_data) == 0:
            return jsonify({"error": "Empty archive"}), 400
        
        with lock:
            global frontend_archive, frontend_timestamp, frontend_uploaded_by
            frontend_archive = archive_data
            frontend_timestamp = time.time()
            frontend_uploaded_by = client_id
        
        print(f"[UPLOAD] frontend.zip by {client_id} ({len(archive_data)} bytes)")
        return jsonify({
            "status": "success",
            "folder": "frontend",
            "size": len(archive_data),
            "timestamp": frontend_timestamp
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload/backend', methods=['POST'])
def upload_backend():
    """Upload backend folder as ZIP"""
    try:
        client_id = request.form.get('client_id', 'unknown')
        
        if 'archive' not in request.files:
            return jsonify({"error": "No archive file provided"}), 400
        
        archive_file = request.files['archive']
        archive_data = archive_file.read()
        
        if len(archive_data) == 0:
            return jsonify({"error": "Empty archive"}), 400
        
        with lock:
            global backend_archive, backend_timestamp, backend_uploaded_by
            backend_archive = archive_data
            backend_timestamp = time.time()
            backend_uploaded_by = client_id
        
        print(f"[UPLOAD] backend.zip by {client_id} ({len(archive_data)} bytes)")
        return jsonify({
            "status": "success",
            "folder": "backend",
            "size": len(archive_data),
            "timestamp": backend_timestamp
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/frontend', methods=['GET'])
def download_frontend():
    """Download frontend folder as ZIP"""
    with lock:
        if frontend_archive is None:
            return jsonify({"error": "frontend archive not found"}), 404
        
        return send_file(
            io.BytesIO(frontend_archive),
            mimetype='application/zip',
            as_attachment=True,
            download_name='frontend.zip'
        )

@app.route('/download/backend', methods=['GET'])
def download_backend():
    """Download backend folder as ZIP"""
    with lock:
        if backend_archive is None:
            return jsonify({"error": "backend archive not found"}), 404
        
        return send_file(
            io.BytesIO(backend_archive),
            mimetype='application/zip',
            as_attachment=True,
            download_name='backend.zip'
        )

@app.route('/info', methods=['GET'])
def get_info():
    """Get information about stored archives"""
    with lock:
        info = {
            "frontend": {
                "exists": frontend_archive is not None,
                "size": len(frontend_archive) if frontend_archive else 0,
                "timestamp": frontend_timestamp,
                "uploaded_by": frontend_uploaded_by
            },
            "backend": {
                "exists": backend_archive is not None,
                "size": len(backend_archive) if backend_archive else 0,
                "timestamp": backend_timestamp,
                "uploaded_by": backend_uploaded_by
            }
        }
        return jsonify(info), 200

if __name__ == '__main__':
    print("=" * 60)
    print("  SIMPLE FILE SYNC SERVER - ZIP ARCHIVE MODE")
    print("=" * 60)
    print("\nServer stores frontend and backend as ZIP archives")
    print("One person at a time for safety")
    print("\nServer URL: http://0.0.0.0:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)


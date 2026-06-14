"""
Tracker Project - Backend Server
Flask API per gestione dispositivi e tracking GPS in tempo reale
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import sqlite3
import json
import os
import logging

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE = 'tracker.db'
DEVICES_FILE = 'devices.json'

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Inizializza il database con le tabelle necessarie"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        owner TEXT,
        device_type TEXT DEFAULT 'mobile',
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_update DATETIME
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        accuracy REAL,
        speed REAL,
        altitude REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        action TEXT,
        details TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_db_connection():
    """Ottiene connessione al database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Converte una riga del database in dizionario"""
    if row is None:
        return None
    return dict(row)

# ========================================================================= 
# API ENDPOINTS - DISPOSITIVI
# =========================================================================

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """GET /api/devices - Ritorna la lista di tutti i dispositivi"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices ORDER BY created_at DESC')
        devices = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(devices),
            'devices': devices
        }), 200
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """GET /api/devices/<device_id> - Ritorna i dettagli di un dispositivo"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        device = cursor.fetchone()
        conn.close()
        
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        return jsonify({
            'success': True,
            'device': dict_from_row(device)
        }), 200
    except Exception as e:
        logger.error(f"Error getting device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices', methods=['POST'])
def create_device():
    """POST /api/devices - Crea un nuovo dispositivo"""
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data:
            return jsonify({'success': False, 'error': 'Missing device_id'}), 400
        
        required_fields = ['device_id', 'name', 'owner']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': f'Missing fields: {required_fields}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO devices (device_id, name, owner, device_type)
            VALUES (?, ?, ?, ?)
            ''', (
                data['device_id'],
                data['name'],
                data['owner'],
                data.get('device_type', 'mobile')
            ))
            conn.commit()
            
            cursor.execute('''
            INSERT INTO tracking_history (device_id, action, details)
            VALUES (?, ?, ?)
            ''', (data['device_id'], 'CREATED', 'Device registered'))
            conn.commit()
            
            logger.info(f"Device created: {data['device_id']}")
            
            conn.close()
            return jsonify({
                'success': True,
                'message': 'Device created successfully',
                'device_id': data['device_id']
            }), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'error': 'Device ID already exists'}), 409
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """DELETE /api/devices/<device_id> - Elimina un dispositivo"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        conn.close()
        logger.info(f"Device deleted: {device_id}")
        
        return jsonify({
            'success': True,
            'message': 'Device deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================================================================
# API ENDPOINTS - TRACKING GPS
# =========================================================================

@app.route('/api/track', methods=['POST'])
def track_location():
    """POST /api/track - Riceve e salva una posizione GPS"""
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data:
            return jsonify({'success': False, 'error': 'Missing device_id'}), 400
        
        required_fields = ['device_id', 'latitude', 'longitude']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': f'Missing fields: {required_fields}'}), 400
        
        device_id = data['device_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        cursor.execute('''
        INSERT INTO locations (device_id, latitude, longitude, accuracy, speed, altitude)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            device_id,
            data['latitude'],
            data['longitude'],
            data.get('accuracy'),
            data.get('speed'),
            data.get('altitude')
        ))
        
        cursor.execute('''
        UPDATE devices SET last_update = CURRENT_TIMESTAMP WHERE device_id = ?
        ''', (device_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Location tracked for {device_id}: ({data['latitude']}, {data['longitude']})")
        
        return jsonify({
            'success': True,
            'message': 'Location tracked successfully',
            'timestamp': datetime.now().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error tracking location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locations/<device_id>', methods=['GET'])
def get_locations(device_id):
    """GET /api/locations/<device_id> - Ritorna tutte le posizioni registrate"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        cursor.execute('SELECT COUNT(*) as count FROM locations WHERE device_id = ?', (device_id,))
        total = cursor.fetchone()['count']
        
        cursor.execute('''
        SELECT * FROM locations 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
        ''', (device_id, limit, offset))
        
        locations = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'total': total,
            'limit': limit,
            'offset': offset,
            'locations': locations
        }), 200
    except Exception as e:
        logger.error(f"Error getting locations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locations/<device_id>/latest', methods=['GET'])
def get_latest_location(device_id):
    """GET /api/locations/<device_id>/latest - Ritorna l'ultima posizione"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM locations 
        WHERE device_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        ''', (device_id,))
        
        location = cursor.fetchone()
        conn.close()
        
        if not location:
            return jsonify({'success': False, 'error': 'No location found'}), 404
        
        return jsonify({
            'success': True,
            'location': dict_from_row(location)
        }), 200
    except Exception as e:
        logger.error(f"Error getting latest location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================================================================
# API ENDPOINTS - STATISTICHE
# =========================================================================

@app.route('/api/stats/all', methods=['GET'])
def get_all_stats():
    """GET /api/stats/all - Ritorna statistiche generali"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM devices')
        total_devices = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM locations')
        total_locations = cursor.fetchone()['count']
        
        cursor.execute('''
        SELECT COUNT(DISTINCT device_id) as count FROM locations 
        WHERE timestamp > datetime('now', '-1 day')
        ''')
        active_devices = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_devices': total_devices,
                'total_locations': total_locations,
                'active_devices': active_devices,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================================================================
# HEALTH CHECK
# =========================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Pagina principale - Dashboard"""
    return render_template('dashboard.html')

# =========================================================================
# ERROR HANDLERS
# =========================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# =========================================================================
# MAIN
# =========================================================================

if __name__ == '__main__':
    init_database()
    logger.info("Starting Tracker Server...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )

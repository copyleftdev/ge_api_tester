import json
import time
import random
import re
import logging
import sqlite3
import os
import functools
from datetime import datetime
from flask import Flask, request, jsonify, g, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Flask-Limiter configuration
# Check if we're running in Docker and set higher limits accordingly
if os.path.exists("/.dockerenv"):
    # Much higher limits for Docker testing environment
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["500 per minute", "10000 per hour"],
        storage_uri="memory://",
    )
    logger.info("Running in Docker: using high rate limits for testing")
else:
    # Standard limits for non-Docker environments
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute", "5000 per hour"],
        storage_uri="memory://",
    )

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db_path = app.config.get('DATABASE_PATH', '/tmp/api_database.db')
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        age INTEGER,
        zipcode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hobbies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        hobby TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        status_code INTEGER,
        response_time REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    db.commit()
    
    if app.config.get('TESTING', False):
        try:
            cursor.execute(
                "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                ("Test User", "test_user@example.com", 30, datetime.now().isoformat())
            )
            db.commit()
        except sqlite3.IntegrityError:
            pass

with app.app_context():
    init_db()

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if request.method != 'OPTIONS':
        response_time = time.time() - getattr(g, 'start_time', time.time())
        
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO access_logs (endpoint, ip_address, status_code, response_time) VALUES (?, ?, ?, ?)",
                (request.path, request.remote_addr, response.status_code, response_time)
            )
            db.commit()
        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response

def validate_token(token):
    if not token:
        return False, None
    
    token_parts = token.split('.')
    if len(token_parts) != 3:
        return False, None
    
    payload = token_parts[1]
    payload_parts = payload.split(':')
    if len(payload_parts) != 2:
        return False, None
    
    try:
        user_id = int(payload_parts[0])
        timestamp = int(payload_parts[1])
        
        current_time = int(time.time())
        if current_time > timestamp + 3600:
            return False, None
        
        return True, user_id
    except (ValueError, TypeError):
        return False, None

def get_auth_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  
    return None

def requires_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token()
        is_valid, user_id = validate_token(token)
        
        if not is_valid:
            return jsonify({"error": "Invalid or missing authentication token"}), 401
        
        return f(user_id, *args, **kwargs)
    
    return decorated

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/auth/token', methods=['POST'])
@limiter.limit("50 per minute" if not os.path.exists("/.dockerenv") else "1000 per minute")
def get_token():
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    username = data['username']
    password = data['password']
    
    if len(password) < 8:
        return jsonify({"error": "Invalid credentials"}), 401
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        if app.config.get('TESTING', False):
            cursor.execute("SELECT * FROM users LIMIT 1")
            user = cursor.fetchone()
            
            if not user:
                cursor.execute(
                    "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                    ("Test User", "test@example.com", 30, datetime.now().isoformat())
                )
                db.commit()
                
                cursor.execute("SELECT * FROM users LIMIT 1")
                user = cursor.fetchone()
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (username,))
            user = cursor.fetchone()
            
            if not user:
                if username == 'admin' and 'admin' in password:
                    return jsonify({"error": "Account locked - too many login attempts"}), 403
                
                cursor.execute(
                    "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                    (username, username, random.randint(18, 65), datetime.now().isoformat())
                )
                db.commit()
                
                cursor.execute("SELECT * FROM users WHERE email = ?", (username,))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({"error": "Failed to create user account"}), 500
        
        user_id = user['id']
        timestamp = int(time.time())
        token_payload = f"{user_id}:{timestamp}"
        token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{token_payload}.signature"
        
        expires_in = 3600
        expires_at = timestamp + expires_in
        
        try:
            cursor.execute(
                "INSERT INTO access_logs (endpoint, ip_address, status_code, response_time) VALUES (?, ?, ?, ?)",
                ('/api/auth/token', request.remote_addr, 200, time.time() - g.start_time)
            )
            db.commit()
        except Exception as e:
            logger.error(f"Error logging auth: {str(e)}")
        
        return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": expires_at,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/api/users', methods=['POST'])
@requires_auth
def create_user(auth_user_id):
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' not in data or not data['name']:
        return jsonify({"error": "Name is required"}), 400
    
    if len(data['name']) < 3 or len(data['name']) > 50:
        return jsonify({"error": "Name must be between 3 and 50 characters"}), 400
    
    if 'email' in data and data['email']:
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, data['email']):
            return jsonify({"error": "Invalid email format"}), 400
    
    if 'age' in data and data['age'] is not None:
        try:
            age = int(data['age'])
            if age < 0 or age > 120:
                return jsonify({"error": "Age must be between 0 and 120"}), 400
        except ValueError:
            return jsonify({"error": "Age must be a valid number"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        name = data['name']
        email = data.get('email')
        age = data.get('age')
        zipcode = data.get('zipcode')
        hobbies = data.get('hobbies', [])
        
        cursor.execute(
            "INSERT INTO users (name, email, age, zipcode, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, age, zipcode, datetime.now().isoformat())
        )
        
        user_id = cursor.lastrowid
        
        if hobbies:
            for hobby in hobbies:
                cursor.execute(
                    "INSERT INTO hobbies (user_id, hobby) VALUES (?, ?)",
                    (user_id, hobby)
                )
        
        db.commit()
        
        return jsonify({
            "id": user_id,
            "name": name,
            "email": email,
            "age": age,
            "zipcode": zipcode,
            "hobbies": hobbies,
            "created_at": datetime.now().isoformat()
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
@requires_auth
def get_user(auth_user_id, user_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        cursor.execute("SELECT hobby FROM hobbies WHERE user_id = ?", (user_id,))
        hobbies = [row[0] for row in cursor.fetchall()]
        
        return jsonify({
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "age": user['age'],
            "zipcode": user['zipcode'],
            "hobbies": hobbies,
            "created_at": user['created_at']
        })
        
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users', methods=['GET'])
@requires_auth
def list_users(auth_user_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 10, type=int), 100)  
        offset = (page - 1) * limit
        
        cursor.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, offset))
        users = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        result = []
        for user in users:
            cursor.execute("SELECT hobby FROM hobbies WHERE user_id = ?", (user['id'],))
            hobbies = [row[0] for row in cursor.fetchall()]
            
            result.append({
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "age": user['age'],
                "zipcode": user['zipcode'],
                "hobbies": hobbies,
                "created_at": user['created_at']
            })
        
        return jsonify({
            "users": result,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit  
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@requires_auth
def update_user(auth_user_id, user_id):
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if 'name' in data:
            if len(data['name']) < 3 or len(data['name']) > 50:
                return jsonify({"error": "Name must be between 3 and 50 characters"}), 400
        
        if 'email' in data and data['email']:
            email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
            if not re.match(email_pattern, data['email']):
                return jsonify({"error": "Invalid email format"}), 400
        
        if 'age' in data and data['age'] is not None:
            try:
                age = int(data['age'])
                if age < 0 or age > 120:
                    return jsonify({"error": "Age must be between 0 and 120"}), 400
            except ValueError:
                return jsonify({"error": "Age must be a valid number"}), 400
        
        update_fields = []
        values = []
        
        if 'name' in data:
            update_fields.append("name = ?")
            values.append(data['name'])
        
        if 'email' in data:
            update_fields.append("email = ?")
            values.append(data['email'])
        
        if 'age' in data:
            update_fields.append("age = ?")
            values.append(data['age'])
        
        if 'zipcode' in data:
            update_fields.append("zipcode = ?")
            values.append(data['zipcode'])
        
        values.append(user_id)
        
        if update_fields:
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, values)
        
        if 'hobbies' in data:
            cursor.execute("DELETE FROM hobbies WHERE user_id = ?", (user_id,))
            
            for hobby in data['hobbies']:
                cursor.execute(
                    "INSERT INTO hobbies (user_id, hobby) VALUES (?, ?)",
                    (user_id, hobby)
                )
        
        db.commit()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = cursor.fetchone()
        
        cursor.execute("SELECT hobby FROM hobbies WHERE user_id = ?", (user_id,))
        hobbies = [row[0] for row in cursor.fetchall()]
        
        return jsonify({
            "id": updated_user['id'],
            "name": updated_user['name'],
            "email": updated_user['email'],
            "age": updated_user['age'],
            "zipcode": updated_user['zipcode'],
            "hobbies": hobbies,
            "created_at": updated_user['created_at']
        })
        
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@requires_auth
def delete_user(auth_user_id, user_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        cursor.execute("DELETE FROM hobbies WHERE user_id = ?", (user_id,))
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        db.commit()
        
        return jsonify({"status": "success", "message": f"User {user_id} deleted"})
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    new_data = {
        "name": data.get('name', ''),
        "age": data.get('age')
    }
    
    if 'email' in data:
        new_data['email'] = data['email']
    if 'zipcode' in data:
        new_data['zipcode'] = data['zipcode']
    if 'hobbies' in data:
        new_data['hobbies'] = data['hobbies']
    
    logger.info(f"Legacy API call received: {json.dumps(data)}")
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            "INSERT INTO access_logs (endpoint, ip_address, status_code, response_time) VALUES (?, ?, ?, ?)",
            ('/predict (legacy)', request.remote_addr, 200, 0)
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error logging legacy API call: {str(e)}")
    
    name = data.get('name', '')
    if not name:
        return jsonify({"error": "Name is required"}), 400
    
    logger.info(f"Processed data for: {name}")
    
    response = {"prediction": random.random(), "processed": True}
    
    if 'zipcode' in data and data['zipcode'] == '90210':
        return jsonify({"error": "Database connection error"}), 500
    
    if 'memleak' in data and data['memleak'] == True:
        time.sleep(2)
        return jsonify({"error": "Server resource exhausted"}), 503
    
    if random.random() < 0.05:
        return jsonify({"error": "Internal server error"}), 500
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

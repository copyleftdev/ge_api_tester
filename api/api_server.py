"""
Enhanced API Server with more realistic features and endpoints
"""
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Rate limiting configuration
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute", "3000 per hour"],
    storage_uri="memory://",
)

# Initialize database
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
    """Initialize the database by creating tables if they don't exist."""
    db = get_db()
    cursor = db.cursor()
    
    # Create users table
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
    
    # Create hobbies table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hobbies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        hobby TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create access logs table
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
    
    # For testing purposes, add a test user
    if app.config.get('TESTING', False):
        try:
            cursor.execute(
                "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                ("Test User", "test_user@example.com", 30, datetime.now().isoformat())
            )
            db.commit()
        except sqlite3.IntegrityError:
            # User already exists, which is fine
            pass

# Initialize database when the app starts
with app.app_context():
    init_db()

# Request tracking middleware
@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    # Skip logging for OPTIONS requests
    if request.method != 'OPTIONS':
        # Calculate response time - safely check if start_time exists
        response_time = time.time() - getattr(g, 'start_time', time.time())
        
        # Log the request to database
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
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response

# Add helper functions for token validation
def validate_token(token):
    """
    Validate an authentication token
    
    Args:
        token: The authentication token to validate
        
    Returns:
        Tuple containing (is_valid, user_id)
    """
    if not token:
        return False, None
    
    # For a proper implementation, we would verify the JWT signature
    # and decode the payload to extract user information
    
    # Parse our simplified token format
    try:
        # Skip the header and signature parts
        parts = token.split('.')
        if len(parts) != 3:
            return False, None
        
        payload = parts[1]
        
        # Parse the payload (user_id:timestamp)
        payload_parts = payload.split(':')
        if len(payload_parts) != 2:
            return False, None
        
        user_id = int(payload_parts[0])
        timestamp = int(payload_parts[1])
        
        # Check if token is expired (1 hour validity)
        current_time = int(time.time())
        if current_time - timestamp > 3600:
            return False, None
        
        return True, user_id
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return False, None

def get_auth_token():
    """Extract authentication token from request headers"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Format should be "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def requires_auth(f):
    """Decorator to require authentication for an endpoint"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token()
        
        if not token:
            return jsonify({"error": "Authorization required"}), 401
        
        is_valid, user_id = validate_token(token)
        if not is_valid:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Add user_id to kwargs
        kwargs['auth_user_id'] = user_id
        return f(*args, **kwargs)
    
    return decorated

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/auth/token', methods=['POST'])
@limiter.limit("10 per minute")
def get_token():
    """Authentication endpoint that verifies user credentials and generates tokens"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Basic validation
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    username = data['username']
    password = data['password']
    
    # Password complexity check
    if len(password) < 8:
        return jsonify({"error": "Invalid credentials"}), 401
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # For testing environment, accept any valid credentials
        if app.config.get('TESTING', False):
            # Get any user from the database for testing
            cursor.execute("SELECT * FROM users LIMIT 1")
            user = cursor.fetchone()
            
            if not user:
                # Create a test user if none exists
                cursor.execute(
                    "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                    ("Test User", "test@example.com", 30, datetime.now().isoformat())
                )
                db.commit()
                
                cursor.execute("SELECT * FROM users LIMIT 1")
                user = cursor.fetchone()
        else:
            # Normal production authentication flow
            # Check if user exists in the database
            cursor.execute("SELECT * FROM users WHERE email = ?", (username,))
            user = cursor.fetchone()
            
            # If user doesn't exist, create one for testing purposes
            if not user:
                # For predefined test credentials, simulate specific responses
                if username == 'admin' and 'admin' in password:
                    return jsonify({"error": "Account locked - too many login attempts"}), 403
                
                # Auto-register user (for testing purposes)
                cursor.execute(
                    "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                    (username, username, random.randint(18, 65), datetime.now().isoformat())
                )
                db.commit()
                
                # Get the newly created user
                cursor.execute("SELECT * FROM users WHERE email = ?", (username,))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({"error": "Failed to create user account"}), 500
        
        # Generate token with user information encoded
        user_id = user['id']
        timestamp = int(time.time())
        # More realistic token structure (still not using JWT but follows similar format)
        token_payload = f"{user_id}:{timestamp}"
        token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{token_payload}.signature"
        
        # Token lifetime in seconds (1 hour)
        expires_in = 3600
        expires_at = timestamp + expires_in
        
        # Log successful login
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

# --- User Management Endpoints ---

@app.route('/api/users', methods=['POST'])
@limiter.limit("30 per minute")
@requires_auth
def create_user(auth_user_id):
    """Create a new user"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    if 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
    
    # Validate name length
    if len(data.get('name', '')) < 3 or len(data.get('name', '')) > 50:
        return jsonify({"error": "Name must be between 3 and 50 characters"}), 400
    
    # Validate email format if provided
    if 'email' in data and data['email']:
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, data['email']):
            return jsonify({"error": "Invalid email format"}), 400
    
    # Validate age if provided
    if 'age' in data and data['age'] is not None:
        try:
            age = int(data['age'])
            if age < 0 or age > 120:
                return jsonify({"error": "Age must be between 0 and 120"}), 400
        except ValueError:
            return jsonify({"error": "Age must be a valid number"}), 400
    
    # Validate zipcode if provided
    if 'zipcode' in data and data['zipcode']:
        # Specific zipcodes trigger server errors (simulating DB issues)
        if data['zipcode'] == '90210':
            return jsonify({"error": "Database connection error"}), 500
        
        # Check zipcode format (basic US format)
        if not re.match(r'^\d{5}(-\d{4})?$', data['zipcode']):
            return jsonify({"error": "Invalid US zipcode format"}), 400
    
    # Validate hobbies if provided
    if 'hobbies' in data and data['hobbies']:
        if not isinstance(data['hobbies'], list):
            return jsonify({"error": "Hobbies must be a list"}), 400
        
        # Check for restricted hobbies
        restricted_hobbies = ['hacking', 'fraud', 'illegal activities']
        for hobby in data['hobbies']:
            if any(restricted in hobby.lower() for restricted in restricted_hobbies):
                return jsonify({"error": "One or more hobbies are restricted"}), 400
    
    # SQL Injection Simulation
    if 'name' in data and "'" in data['name']:
        if 'DROP TABLE' in data['name'].upper() or 'DELETE FROM' in data['name'].upper():
            # Simulate SQL injection vulnerability
            return jsonify({"error": "SQL syntax error"}), 500
    
    # Memory leak simulation
    if 'memleak' in data and data['memleak'] == True:
        # Just simulate a memory leak with a slow response
        time.sleep(2)
        return jsonify({"error": "Server resource exhausted"}), 503
    
    # Random server error (5% chance)
    if random.random() < 0.05:
        return jsonify({"error": "Internal server error"}), 500
    
    try:
        # Save user to database
        db = get_db()
        cursor = db.cursor()
        
        # Insert user record
        cursor.execute(
            "INSERT INTO users (name, email, age, zipcode) VALUES (?, ?, ?, ?)",
            (data.get('name'), data.get('email'), data.get('age'), data.get('zipcode'))
        )
        user_id = cursor.lastrowid
        
        # Insert hobbies if provided
        if 'hobbies' in data and data['hobbies']:
            for hobby in data['hobbies']:
                cursor.execute(
                    "INSERT INTO hobbies (user_id, hobby) VALUES (?, ?)",
                    (user_id, hobby)
                )
        
        db.commit()
        
        # Return the created user with fake id
        return jsonify({
            "id": user_id,
            "name": data.get('name'),
            "email": data.get('email'),
            "age": data.get('age'),
            "zipcode": data.get('zipcode'),
            "hobbies": data.get('hobbies', []),
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
    """Get user by ID"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user's hobbies
        cursor.execute("SELECT hobby FROM hobbies WHERE user_id = ?", (user_id,))
        hobbies = [row[0] for row in cursor.fetchall()]
        
        # Return user data
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
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users', methods=['GET'])
@requires_auth
def list_users(auth_user_id):
    """List all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 10, type=int), 100)  # Cap at 100
        offset = (page - 1) * limit
        
        db = get_db()
        cursor = db.cursor()
        
        # Get users with pagination
        cursor.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, offset))
        users = cursor.fetchall()
        
        # Count total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        # Process user data
        result = []
        for user in users:
            # Get user's hobbies
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
        
        # Return paginated results
        return jsonify({
            "users": result,
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit  # Ceiling division
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@requires_auth
def update_user(auth_user_id, user_id):
    """Update an existing user"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Validate fields same as create
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
        
        # Build update SQL
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
        
        # Add user_id to values
        values.append(user_id)
        
        # Update user if there are fields to update
        if update_fields:
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, values)
        
        # Update hobbies if provided
        if 'hobbies' in data:
            # Delete existing hobbies
            cursor.execute("DELETE FROM hobbies WHERE user_id = ?", (user_id,))
            
            # Insert new hobbies
            for hobby in data['hobbies']:
                cursor.execute(
                    "INSERT INTO hobbies (user_id, hobby) VALUES (?, ?)",
                    (user_id, hobby)
                )
        
        db.commit()
        
        # Get updated user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = cursor.fetchone()
        
        # Get updated hobbies
        cursor.execute("SELECT hobby FROM hobbies WHERE user_id = ?", (user_id,))
        hobbies = [row[0] for row in cursor.fetchall()]
        
        # Return updated user
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
    """Delete a user"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Delete user's hobbies
        cursor.execute("DELETE FROM hobbies WHERE user_id = ?", (user_id,))
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        db.commit()
        
        return jsonify({"status": "success", "message": f"User {user_id} deleted"})
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# --- Legacy endpoint for backward compatibility ---
@app.route('/predict', methods=['POST'])
def predict():
    """Legacy prediction endpoint - redirects to user creation"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Transform legacy payload format to new format
    new_data = {
        "name": data.get('name', ''),
        "age": data.get('age')
    }
    
    # Optional fields
    if 'email' in data:
        new_data['email'] = data['email']
    if 'zipcode' in data:
        new_data['zipcode'] = data['zipcode']
    if 'hobbies' in data:
        new_data['hobbies'] = data['hobbies']
    
    # Log the legacy request
    logger.info(f"Legacy API call received: {json.dumps(data)}")
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Record the legacy API call for analytics
        cursor.execute(
            "INSERT INTO access_logs (endpoint, ip_address, status_code, response_time) VALUES (?, ?, ?, ?)",
            ('/predict (legacy)', request.remote_addr, 200, 0)
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error logging legacy API call: {str(e)}")
    
    # Process with minimal validation (for backward compatibility)
    name = data.get('name', '')
    if not name:
        return jsonify({"error": "Name is required"}), 400
    
    logger.info(f"Processed data for: {name}")
    
    # Return dummy response to maintain backward compatibility
    response = {"prediction": random.random(), "processed": True}
    
    # Add legacy simulation behaviors
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

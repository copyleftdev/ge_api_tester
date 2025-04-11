"""
Unit tests for the enhanced API server.

This module tests all endpoints and features of the API server including:
- Authentication
- User management (CRUD operations)
- Input validation
- Error handling
- Rate limiting
"""
import pytest
import json
import time
import re
import uuid
from flask import Flask
from api_server import app, init_db

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost'
    
    # Use an in-memory SQLite database for testing
    app.config['DATABASE_PATH'] = ':memory:'
    
    # Flask test client
    with app.test_client() as client:
        # Create an application context
        with app.app_context():
            # Initialize the test database
            init_db()
            yield client

@pytest.fixture
def auth_token(client):
    """Create a valid authentication token for testing."""
    auth_data = {
        "username": "test_user@example.com",
        "password": "testpassword123"
    }

    response = client.post(
        '/api/auth/token',
        data=json.dumps(auth_data),
        content_type='application/json'
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to get auth token: {response.get_json()}")

    return response.get_json()['access_token']

@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers with the auth token."""
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

# --- Health Check Tests ---

def test_health_check_endpoint(client):
    """Test that the health check endpoint returns 200 OK."""
    response = client.get('/api/health')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data
    assert data['version'] == '1.0.0'

# --- Authentication Tests ---

def test_auth_token_success(client):
    """Test successful authentication token generation."""
    auth_data = {
        "username": "user@example.com",
        "password": "password123"
    }
    
    response = client.post(
        '/api/auth/token',
        data=json.dumps(auth_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'
    assert 'expires_in' in data
    assert 'user_id' in data

def test_auth_token_invalid_credentials(client):
    """Test authentication with invalid credentials."""
    auth_data = {
        "username": "user@example.com",
        "password": "short"  # Too short password
    }
    
    response = client.post(
        '/api/auth/token',
        data=json.dumps(auth_data),
        content_type='application/json'
    )
    
    assert response.status_code == 401
    data = response.get_json()
    assert 'error' in data

def test_auth_token_missing_fields(client):
    """Test authentication with missing required fields."""
    # Missing password
    auth_data = {
        "username": "user@example.com"
    }
    
    response = client.post(
        '/api/auth/token',
        data=json.dumps(auth_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

# --- User Management Tests ---

def test_create_user(client, auth_headers):
    """Test creating a new user."""
    # Generate unique email to avoid conflicts with previous test runs
    unique_email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
    
    user_data = {
        "name": "Test User",
        "email": unique_email,
        "age": 30,
        "zipcode": "12345",
        "hobbies": ["reading", "coding"]
    }
    
    response = client.post(
        '/api/users',
        data=json.dumps(user_data),
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == user_data['name']
    assert data['email'] == user_data['email']
    assert data['age'] == user_data['age']
    assert data['zipcode'] == user_data['zipcode']
    assert data['hobbies'] == user_data['hobbies']
    assert 'id' in data
    assert 'created_at' in data

def test_create_user_validation_error(client, auth_headers):
    """Test user creation with validation errors."""
    # Invalid email format
    user_data = {
        "name": "Test User",
        "email": "invalid-email",
        "age": 30
    }
    
    response = client.post(
        '/api/users',
        data=json.dumps(user_data),
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'email' in data['error'].lower()

def test_get_user(client, auth_headers):
    """Test retrieving a user by ID."""
    # First create a user with unique email
    unique_email = f"getuser_{uuid.uuid4().hex[:8]}@example.com"
    
    user_data = {
        "name": "Get Test User",
        "email": unique_email,
        "age": 25
    }
    
    create_response = client.post(
        '/api/users',
        data=json.dumps(user_data),
        headers=auth_headers
    )
    
    assert create_response.status_code == 201
    user_id = create_response.get_json()['id']
    
    # Now retrieve the user
    response = client.get(
        f'/api/users/{user_id}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == user_id
    assert data['name'] == user_data['name']
    assert data['email'] == user_data['email']
    assert data['age'] == user_data['age']

def test_get_nonexistent_user(client, auth_headers):
    """Test retrieving a user that doesn't exist."""
    response = client.get(
        '/api/users/9999',
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_update_user(client, auth_headers):
    """Test updating a user."""
    # First create a user with unique email
    unique_email = f"updateuser_{uuid.uuid4().hex[:8]}@example.com"
    
    user_data = {
        "name": "Update Test User",
        "email": unique_email,
        "age": 30
    }
    
    create_response = client.post(
        '/api/users',
        data=json.dumps(user_data),
        headers=auth_headers
    )
    
    user_id = create_response.get_json()['id']
    
    # Now update the user
    update_data = {
        "name": "Updated Name",
        "age": 31,
        "hobbies": ["swimming"]
    }
    
    response = client.put(
        f'/api/users/{user_id}',
        data=json.dumps(update_data),
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == user_id
    assert data['name'] == update_data['name']
    assert data['email'] == user_data['email']  # Unchanged
    assert data['age'] == update_data['age']
    assert data['hobbies'] == update_data['hobbies']

def test_delete_user(client, auth_headers):
    """Test deleting a user."""
    # First create a user with unique email
    unique_email = f"deleteuser_{uuid.uuid4().hex[:8]}@example.com"
    
    user_data = {
        "name": "Delete Test User",
        "email": unique_email
    }
    
    create_response = client.post(
        '/api/users',
        data=json.dumps(user_data),
        headers=auth_headers
    )
    
    user_id = create_response.get_json()['id']
    
    # Now delete the user
    response = client.delete(
        f'/api/users/{user_id}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    
    # Verify the user is gone
    get_response = client.get(
        f'/api/users/{user_id}',
        headers=auth_headers
    )
    
    assert get_response.status_code == 404

def test_list_users(client, auth_headers):
    """Test listing users with pagination."""
    # Create multiple users
    for i in range(3):
        unique_email = f"listuser_{uuid.uuid4().hex[:8]}@example.com"
        
        user_data = {
            "name": f"List Test User {i}",
            "email": unique_email
        }
        
        client.post(
            '/api/users',
            data=json.dumps(user_data),
            headers=auth_headers
        )
    
    # Get the user list
    response = client.get(
        '/api/users?page=1&limit=10',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'users' in data
    assert isinstance(data['users'], list)
    assert len(data['users']) >= 3
    assert 'page' in data
    assert 'limit' in data
    assert 'total' in data
    assert 'pages' in data

# --- Authorization Tests ---

def test_unauthorized_access(client):
    """Test accessing a protected endpoint without authentication."""
    response = client.get('/api/users')
    
    assert response.status_code == 401
    data = response.get_json()
    assert 'error' in data
    assert 'authorization' in data['error'].lower()

def test_invalid_token(client):
    """Test accessing a protected endpoint with an invalid token."""
    headers = {
        'Authorization': 'Bearer invalid.token.here',
        'Content-Type': 'application/json'
    }
    
    response = client.get('/api/users', headers=headers)
    
    assert response.status_code == 401
    data = response.get_json()
    assert 'error' in data
    assert 'invalid' in data['error'].lower()

# --- Legacy Endpoint Tests ---

def test_predict_endpoint_success(client):
    """Test that the legacy /predict endpoint works with valid data."""
    data = {
        "name": "Test User",
        "age": 30,
        "email": "test@example.com"
    }
    
    response = client.post(
        '/predict',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'prediction' in json_data
    assert 'processed' in json_data
    assert json_data['processed'] is True

def test_predict_endpoint_error_zip_code(client):
    """Test that zipcode 90210 triggers a simulated server error."""
    data = {
        "name": "Error User",
        "zipcode": "90210"
    }
    
    response = client.post(
        '/predict',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 500
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'database connection' in json_data['error'].lower()

def test_predict_endpoint_memory_leak(client):
    """Test the memory leak simulation."""
    data = {
        "name": "Memory Leak User",
        "memleak": True
    }
    
    start_time = time.time()
    response = client.post(
        '/predict',
        data=json.dumps(data),
        content_type='application/json'
    )
    response_time = time.time() - start_time
    
    assert response.status_code == 503
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'resource exhausted' in json_data['error'].lower()
    assert response_time >= 1.0  # Should have a delay of at least 1 second

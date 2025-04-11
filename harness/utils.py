"""
Utility functions for the genetic evolution API tester

This module contains helper functions for evaluating API responses and normalizing fitness scores.
Enhancements include support for our more realistic API endpoints with proper fitness evaluation.
"""
import json
import time
import random
import logging
import requests
from typing import Dict, Any, Tuple, List, Optional
import statistics
from urllib.parse import urljoin
import os
import threading  # Import threading module

# Import payload tracker for saving interesting payloads
from payload_tracker import payload_tracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- API Configuration ---
# Use API container service name when running in Docker, localhost otherwise
API_HOST = "api" if os.path.exists("/.dockerenv") else "localhost"
API_BASE_URL = f"http://{API_HOST}:5000/"
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3

# Authentication state (token storage)
AUTH_TOKEN = None
AUTH_EXPIRY = 0
TOKEN_LOCK = threading.Lock()  # Lock for thread-safe token access

# --- Fitness Evaluation Parameters ---
# Define weights for different aspects of API response evaluation
WEIGHTS = {
    "status_code": 0.3,       # Weight for HTTP status code evaluation
    "response_time": 0.2,     # Weight for response time evaluation
    "response_content": 0.3,  # Weight for response content evaluation
    "error_message": 0.2      # Weight for specific error message patterns
}

# Define specific status codes we're interested in discovering
TARGET_STATUS_CODES = {
    400: 0.5,   # Bad Request - validation errors
    401: 0.6,   # Unauthorized
    403: 0.7,   # Forbidden
    404: 0.3,   # Not Found
    409: 0.6,   # Conflict
    422: 0.5,   # Unprocessable Entity
    429: 0.7,   # Too Many Requests
    500: 0.8,   # Internal Server Error
    503: 0.9    # Service Unavailable
}

# Define response time thresholds
RESPONSE_TIME_THRESHOLDS = {
    "slow": 1.0,      # Seconds - slow responses
    "very_slow": 1.5  # Seconds - very slow responses (potential resource issues)
}

# Define interesting error message patterns to look for
ERROR_PATTERNS = [
    "SQL",
    "syntax error",
    "database",
    "memory",
    "resource exhausted",
    "injection",
    "overflow",
    "buffer",
    "validation",
    "timeout",
    "unavailable"
]

def select_endpoint(payload: Dict[str, Any]) -> str:
    """
    Select the appropriate API endpoint based on the payload content.
    
    Args:
        payload: The payload to be sent to the API
        
    Returns:
        str: The API endpoint URL
    """
    # Check payload keys to determine the most appropriate endpoint
    if "username" in payload and "password" in payload:
        return urljoin(API_BASE_URL, "api/auth/token")
    
    # If it has just typical user fields, use the users endpoint
    if "name" in payload:
        # For user-related operations, default to POST for creation
        return urljoin(API_BASE_URL, "api/users")
        
    # Default to legacy endpoint if we can't determine
    return urljoin(API_BASE_URL, "predict")

def make_api_call(payload: Dict[str, Any], endpoint: Optional[str] = None) -> Tuple[Dict[str, Any], float, int, Dict[str, Any]]:
    """
    Make an API call with the given payload.
    
    Args:
        payload: JSON payload to send
        endpoint: Optional endpoint override, if None will be auto-selected
        
    Returns:
        Tuple containing:
        - Response data as a dictionary (or error info)
        - Response time in seconds
        - HTTP status code
        - Headers as a dictionary
    """
    if endpoint is None:
        endpoint = select_endpoint(payload)
    
    global AUTH_TOKEN, AUTH_EXPIRY
    headers = {
        'Content-Type': 'application/json'
    }
    
    current_time = int(time.time())
    needs_auth = "auth" not in endpoint and endpoint != urljoin(API_BASE_URL, "predict")
    
    # Use a lock to prevent multiple threads from requesting tokens simultaneously
    with TOKEN_LOCK:
        if needs_auth and (AUTH_TOKEN is None or current_time >= AUTH_EXPIRY):
            # Add a random delay between 0.5 and 2 seconds to avoid rate limiting
            time.sleep(random.uniform(0.5, 2.0))
            
            # Share auth tokens between requests to reduce API calls
            auth_payload = {"username": "tester", "password": "test_password"}
            auth_url = urljoin(API_BASE_URL, "api/auth/token")
            
            try:
                auth_response = requests.post(
                    auth_url,
                    json=auth_payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=REQUEST_TIMEOUT
                )
                
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    AUTH_TOKEN = auth_data.get('token')
                    
                    token_lifetime = auth_data.get('expires_in', 3600)
                    AUTH_EXPIRY = current_time + token_lifetime
                    
                    logger.info(f"Obtained new auth token valid for {token_lifetime} seconds")
                elif auth_response.status_code == 429:
                    # If rate limited, wait longer
                    logger.warning(f"Rate limited when obtaining auth token. Waiting...")
                    time.sleep(random.uniform(3.0, 5.0))
                else:
                    logger.warning(f"Failed to obtain auth token: {auth_response.status_code}")
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}")
    
    if needs_auth and AUTH_TOKEN:
        headers['Authorization'] = f"Bearer {AUTH_TOKEN}"
    
    # Initialize response data
    response_data = {}
    status_code = 0
    response_headers = {}
    start_time = time.time()
    
    # Try the API call with retries
    for attempt in range(MAX_RETRIES):
        try:
            if random.random() < 0.05:
                payload_str = json.dumps(payload)
                if random.random() < 0.5:
                    payload_str = payload_str.replace(":", ";")
                elif random.random() < 0.5:
                    payload_str = payload_str.replace(",", ";")
                
                try:
                    corrupted_payload = json.loads(payload_str)
                    response = requests.post(
                        endpoint,
                        json=corrupted_payload,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT
                    )
                except:
                    response = requests.post(
                        endpoint,
                        data=payload_str,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT
                    )
            else:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
            
            # Extract response data
            status_code = response.status_code
            response_headers = dict(response.headers)
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"raw_response": response.text, "error": "Invalid JSON response"}
            
            # Break the retry loop if we got a response
            break
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out on attempt {attempt + 1}/{MAX_RETRIES}")
            response_data = {"error": "Request timed out"}
            status_code = 408
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed on attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")
            response_data = {"error": str(e)}
            status_code = 0
        
        if attempt < MAX_RETRIES - 1:
            time.sleep(1)
    
    # This should not be reached, but just in case
    end_time = time.time()
    response_time = end_time - start_time
    
    if "delay" in payload:
        delay_time = float(payload["delay"])
        logger.info(f"Artificial delay requested: {delay_time}s")
        if delay_time > 0 and delay_time < 5:
            time.sleep(delay_time)
            response_time += delay_time
    
    if "memleak" in payload and payload["memleak"] is True and random.random() < 0.5:
        logger.info("Memory leak simulation requested")
        response_data = {"error": "Resource exhausted: memory allocation failed"}
        status_code = 500
    
    return response_data, response_time, status_code, response_headers

def evaluate_status_code(status_code: int) -> float:
    """
    Evaluate the HTTP status code and assign a fitness score.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        float: Fitness score for the status code (0.0 to 1.0)
    """
    # We're particularly interested in discovering error codes,
    # so they get higher fitness values
    if status_code == 0:
        return 0.0
    
    if status_code in TARGET_STATUS_CODES:
        return TARGET_STATUS_CODES[status_code]
    
    # 2xx codes are success, so they get a moderate score
    elif 200 <= status_code < 300:
        return 0.1
    
    # 3xx codes are redirects, so they get a moderate score
    elif 300 <= status_code < 400:
        return 0.3
    
    # 4xx errors not explicitly targeted get a lower score
    elif 400 <= status_code < 500:
        return 0.4
    
    # 5xx errors not explicitly targeted get a moderate score
    elif 500 <= status_code < 600:
        return 0.7
    
    # Anything else (unusual status codes) get a low score
    return 0.0

def evaluate_response_time(response_time: float) -> float:
    """
    Evaluate the response time and assign a fitness score.
    
    Args:
        response_time: Response time in seconds
        
    Returns:
        float: Fitness score for the response time (0.0 to 1.0)
    """
    # Quicker responses get lower scores, slower responses get higher scores
    # since slow responses might indicate stress or issues in the API
    
    if response_time <= 0:
        return 0.0
    
    if response_time < 0.1:
        return 0.1
    
    if response_time >= RESPONSE_TIME_THRESHOLDS["very_slow"]:
        # Very slow responses are interesting (possible resource issues)
        return 1.0
    
    if response_time >= RESPONSE_TIME_THRESHOLDS["slow"]:
        # Slow responses are somewhat interesting
        return 0.8
    
    # Normalize to the range [0.0, 1.0]
    normalized = min(1.0, response_time / RESPONSE_TIME_THRESHOLDS["very_slow"])
    return normalized

def evaluate_response_content(response_data: Dict[str, Any], status_code: int) -> float:
    """
    Evaluate the content of the response and assign a fitness score.
    
    Args:
        response_data: Response data as a dictionary
        status_code: HTTP status code
        
    Returns:
        float: Fitness score for the response content (0.0 to 1.0)
    """
    if not response_data:
        return 0.0
    
    score = 0.0
    
    response_str = str(response_data).lower()
    
    if 500 <= status_code < 600:
        score += 0.5
    
    if "error" in response_data:
        score += 0.3
    
    if len(response_str) > 1000:
        score += 0.2
    
    if "memory" in response_str or "resource" in response_str:
        score += 0.5
    
    if "database" in response_str or "sql" in response_str:
        score += 0.7
    
    if "injection" in response_str:
        score += 0.9
    
    if "null" in response_str and "error" in response_str:
        score += 0.3
    
    if "token expired" in response_str or "invalid token" in response_str:
        score += 0.4
    
    # Normalize the score to [0.0, 1.0]
    return min(score, 1.0)

def evaluate_error_messages(response_data: Dict[str, Any]) -> float:
    """
    Evaluate error messages in the response for interesting patterns.
    
    Args:
        response_data: Response data as a dictionary
        
    Returns:
        float: Fitness score for error messages (0.0 to 1.0)
    """
    if not response_data:
        return 0.0
    
    response_str = str(response_data).lower()
    score = 0.0
    
    for pattern in ERROR_PATTERNS:
        if pattern.lower() in response_str:
            score += 0.4
            break
    
    if "sql" in response_str or "database" in response_str:
        score += 0.5
        payload_tracker.track_sql_injection(response_data)
    
    if "memory" in response_str or "resource exhausted" in response_str:
        score += 0.6
        payload_tracker.track_memory_issue(response_data)
    
    auth_patterns = ["token", "unauthorized", "authentication", "permission", "access", "forbidden"]
    for pattern in auth_patterns:
        if pattern in response_str and ("error" in response_str or "invalid" in response_str):
            score += 0.5
            break
    
    validation_patterns = ["validation", "invalid", "too long", "too short", "required", "format"]
    for pattern in validation_patterns:
        if pattern in response_str:
            score += 0.3
            break
    
    # Normalize the score to [0.0, 1.0]
    return min(score, 1.0)

def evaluate_candidate(candidate: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate a candidate payload by sending it to the API and analyzing the response.
    
    Args:
        candidate: Candidate payload as a dictionary
        
    Returns:
        Tuple containing:
        - Fitness score (0.0 to 1.0)
        - Response data dictionary with additional metadata
    """
    # Make the API call
    response_data, response_time, status_code, headers = make_api_call(candidate)
    
    # Store response information for future reference
    response_info = {
        "data": response_data,
        "time": response_time,
        "status_code": status_code,
        "headers": headers
    }
    
    # Evaluate different aspects of the response
    status_score = evaluate_status_code(status_code)
    time_score = evaluate_response_time(response_time)
    content_score = evaluate_response_content(response_data, status_code)
    error_score = evaluate_error_messages(response_data)
    
    # Calculate weighted fitness score
    fitness = (
        WEIGHTS["status_code"] * status_score +
        WEIGHTS["response_time"] * time_score +
        WEIGHTS["response_content"] * content_score +
        WEIGHTS["error_message"] * error_score
    )
    
    # Log detailed evaluation for debugging
    logger.debug(f"Fitness evaluation - Status: {status_score:.2f}, Time: {time_score:.2f}, "
                f"Content: {content_score:.2f}, Error: {error_score:.2f}, Total: {fitness:.2f}")
    
    # Track interesting payloads
    track_interesting_payload(candidate, response_info, fitness)
    
    return fitness, response_info

def track_interesting_payload(
    payload: Dict[str, Any], 
    response_info: Dict[str, Any], 
    fitness: float
) -> None:
    """
    Track interesting payloads based on certain criteria.
    
    Args:
        payload: The candidate payload
        response_info: Response information dict
        fitness: Calculated fitness score
    """
    status_code = response_info.get("status_code", 0)
    response_time = response_info.get("time", 0)
    response_data = response_info.get("data", {})
    
    # Track high fitness payloads
    if fitness > 0.6:
        payload_tracker.track_high_fitness(payload, response_info, fitness)
    
    # Track server errors (5xx)
    if 500 <= status_code < 600:
        payload_tracker.track_server_error(payload, response_info)
    
    # Track validation errors (4xx)
    if 400 <= status_code < 500:
        payload_tracker.track_validation_error(payload, response_info)
    
    # Track slow responses
    if response_time >= RESPONSE_TIME_THRESHOLDS["slow"]:
        payload_tracker.track_slow_response(payload, response_info, response_time)
    
    # Track timeouts
    if status_code == 408 or "timeout" in str(response_data).lower():
        payload_tracker.track_timeout(payload, response_info)
    
    # Track auth-related responses
    if status_code in [401, 403] or "token" in str(response_data).lower():
        payload_tracker.track_auth_issue(payload, response_info)

if __name__ == "__main__":
    # Simple test if run directly
    test_payload = {"name": "Test User", "age": 30}
    fitness, response = evaluate_candidate(test_payload)
    print(f"Test fitness: {fitness}")
    print(f"Test response: {json.dumps(response, indent=2)}")

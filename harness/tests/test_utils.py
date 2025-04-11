"""
Unit tests for the utils module.

This module tests the utility functions used by the genetic evolution tester,
including API interaction, fitness evaluation, and response analysis.
"""
import pytest
import json
import mock
import time
import requests
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils
from payload_tracker import payload_tracker

class TestUtils:
    """Tests for the utils module functions."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset any mocks or test state
        pass
    
    @patch('utils.requests.post')
    def test_make_api_call_success(self, mock_post):
        """Test successful API call."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": "test_data"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response
        
        # Test the function
        payload = {"name": "Test User", "age": 30}
        endpoint = "http://api:5000/predict"
        
        # Mock the auth token
        with patch.object(utils, 'AUTH_TOKEN', 'dummy_token'):
            with patch.object(utils, 'AUTH_EXPIRY', int(time.time()) + 3600):
                response_data, response_time, status_code, headers = utils.make_api_call(payload, endpoint)
        
        # Assertions
        assert status_code == 200
        assert response_data == {"status": "success", "data": "test_data"}
        assert "Content-Type" in headers
        assert isinstance(response_time, float)
        mock_post.assert_called_once()
    
    @patch('utils.requests.post')
    def test_make_api_call_retry(self, mock_post):
        """Test API call retry mechanism."""
        # First call fails with network error, second succeeds
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection error"),
            MagicMock(
                status_code=200,
                json=lambda: {"status": "success"},
                headers={"Content-Type": "application/json"}
            )
        ]
        
        # Test the function
        payload = {"name": "Test User"}
        endpoint = "http://api:5000/predict"
        
        response_data, response_time, status_code, headers = utils.make_api_call(payload, endpoint)
        
        # Assertions
        assert status_code == 200
        assert response_data == {"status": "success"}
        assert mock_post.call_count == 2
    
    def test_select_endpoint(self):
        """Test endpoint selection based on payload."""
        # Auth payload
        auth_payload = {"username": "user", "password": "pass"}
        assert utils.select_endpoint(auth_payload).endswith("/api/auth/token")
        
        # User payload
        user_payload = {"name": "Test User"}
        assert utils.select_endpoint(user_payload).endswith("/api/users")
        
        # Legacy payload with no specific indicators
        legacy_payload = {"random": "data"}
        assert utils.select_endpoint(legacy_payload).endswith("/predict")
    
    def test_evaluate_status_code(self):
        """Test status code evaluation."""
        # Test target status codes
        assert utils.evaluate_status_code(400) == utils.TARGET_STATUS_CODES[400]
        assert utils.evaluate_status_code(500) == utils.TARGET_STATUS_CODES[500]
        
        # Test status code ranges
        assert 0 < utils.evaluate_status_code(200) < 1  # Success code
        assert 0 < utils.evaluate_status_code(404) < 1  # Common error
        assert 0 < utils.evaluate_status_code(302) < 1  # Redirect
    
    def test_evaluate_response_time(self):
        """Test response time evaluation."""
        # Very slow response
        assert utils.evaluate_response_time(2.0) > 0.8
        
        # Slow response
        assert utils.evaluate_response_time(1.2) > 0.5
        
        # Normal response
        assert 0 <= utils.evaluate_response_time(0.3) <= 0.5
    
    def test_evaluate_response_content(self):
        """Test response content evaluation."""
        # Error response
        error_response = {"error": "Something went wrong serious SQL error"}
        assert utils.evaluate_response_content(error_response, 400) > 0.5
        
        # Success response with token
        auth_response = {"access_token": "token123", "expires_in": 3600}
        assert utils.evaluate_response_content(auth_response, 200) > 0.2
        
        # Empty response
        assert utils.evaluate_response_content({}, 200) == 0.0
    
    def test_evaluate_error_messages(self):
        """Test error message evaluation."""
        # SQL injection pattern
        sql_error = {"error": "SQL syntax error in query"}
        assert utils.evaluate_error_messages(sql_error) > 0.5
        
        # Memory issue pattern
        memory_error = {"error": "Memory allocation failed"}
        assert utils.evaluate_error_messages(memory_error) > 0.5
        
        # Auth error pattern
        auth_error = {"error": "Invalid authentication token"}
        assert utils.evaluate_error_messages(auth_error) > 0.5
        
        # Generic error
        generic_error = {"error": "Something happened"}
        assert utils.evaluate_error_messages(generic_error) < 0.5
    
    @patch('utils.evaluate_status_code')
    @patch('utils.evaluate_response_time')
    @patch('utils.evaluate_response_content')
    @patch('utils.evaluate_error_messages')
    @patch('utils.track_interesting_payload')
    def test_evaluate_candidate(self, mock_track, mock_eval_error, mock_eval_content, 
                                mock_eval_time, mock_eval_status):
        """Test the candidate evaluation function."""
        # Setup mocks
        mock_eval_status.return_value = 0.5
        mock_eval_time.return_value = 0.3
        mock_eval_content.return_value = 0.7
        mock_eval_error.return_value = 0.4
        
        # Mock the make_api_call function
        with patch('utils.make_api_call') as mock_api_call:
            mock_api_call.return_value = (
                {"status": "success"},  # response data
                0.2,  # response time
                200,  # status code
                {"Content-Type": "application/json"}  # headers
            )
            
            # Test the function
            payload = {"name": "Test User"}
            fitness, response_info = utils.evaluate_candidate(payload)
            
            # Check that fitness is calculated correctly using the mocked components
            expected_fitness = (
                utils.WEIGHTS["status_code"] * 0.5 +
                utils.WEIGHTS["response_time"] * 0.3 +
                utils.WEIGHTS["response_content"] * 0.7 +
                utils.WEIGHTS["error_message"] * 0.4
            )
            assert fitness == expected_fitness
            
            # Check that response info is populated correctly
            assert response_info["status_code"] == 200
            assert response_info["time"] == 0.2
            assert response_info["data"] == {"status": "success"}
            
            # Check that tracking was called
            mock_track.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])

"""
Unit tests for the grammar module.

This module tests the grammar generation functions used to create
payloads for the API testing.
"""
import pytest
import json
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grammar

class TestGrammar:
    """Tests for the grammar module functions."""
    
    def test_generate_name(self):
        """Test name generation."""
        for _ in range(10):
            name = grammar.generate_name()
            assert isinstance(name, str)
            assert 1 <= len(name) <= 50  # Check length constraints
    
    def test_generate_email(self):
        """Test email generation."""
        for _ in range(10):
            email = grammar.generate_email()
            assert isinstance(email, str)
            # Basic email format check
            assert re.match(r"[^@]+@[^@]+\.[^@]+", email)
    
    def test_generate_age(self):
        """Test age generation."""
        for _ in range(10):
            age = grammar.generate_age()
            # Age could be int or string depending on implementation
            assert isinstance(age, (int, str))
            
            # Convert to int if string
            if isinstance(age, str):
                age = int(age)
            
            # Check age bounds
            assert 0 <= age <= 120
    
    def test_generate_zipcode(self):
        """Test zipcode generation."""
        for _ in range(10):
            zipcode = grammar.generate_zipcode()
            assert isinstance(zipcode, str)
            # Basic US zipcode format: 5 digits
            assert len(zipcode) == 5
            assert zipcode.isdigit()
    
    def test_generate_hobbies(self):
        """Test hobbies generation."""
        for _ in range(10):
            hobbies = grammar.generate_hobbies()
            assert isinstance(hobbies, list)
            # Check that we have at least one hobby
            assert len(hobbies) > 0
            # Check that all hobbies are strings
            for hobby in hobbies:
                assert isinstance(hobby, str)
    
    def test_generate_username(self):
        """Test username generation."""
        for _ in range(10):
            username = grammar.generate_username()
            assert isinstance(username, str)
            assert len(username) > 0
    
    def test_generate_password(self):
        """Test password generation."""
        for _ in range(10):
            password = grammar.generate_password()
            assert isinstance(password, str)
            # Passwords should vary in length
            assert len(password) > 0
    
    def test_generate_auth_payload(self):
        """Test auth payload generation."""
        payload = grammar.generate_auth_payload()
        assert isinstance(payload, dict)
        
        # Check required fields
        assert "username" in payload
        assert "password" in payload
        
        # Check field types
        assert isinstance(payload["username"], str)
        assert isinstance(payload["password"], str)
    
    def test_generate_user_payload(self):
        """Test user payload generation."""
        payload = grammar.generate_user_payload()
        assert isinstance(payload, dict)
        
        # User payload should always have a name
        assert "name" in payload
        assert isinstance(payload["name"], str)
        
        # Check optional fields types if present
        if "email" in payload:
            assert isinstance(payload["email"], str)
        if "age" in payload:
            assert isinstance(payload["age"], (int, str))
        if "zipcode" in payload:
            assert isinstance(payload["zipcode"], str)
        if "hobbies" in payload:
            assert isinstance(payload["hobbies"], list)
    
    def test_generate_random_payload(self):
        """Test random payload generation."""
        for _ in range(10):
            payload = grammar.generate_random_payload()
            assert isinstance(payload, dict)
            # Should have at least one field
            assert len(payload) > 0
            
            # All values should be valid JSON types
            for value in payload.values():
                # Try to serialize to JSON to check validity
                try:
                    json.dumps(value)
                except (TypeError, OverflowError):
                    pytest.fail(f"Value {value} is not JSON serializable")
    
    def test_crossover_payloads(self):
        """Test payload crossover function."""
        payload1 = {"name": "User1", "age": 25, "email": "user1@example.com"}
        payload2 = {"name": "User2", "zipcode": "12345", "hobbies": ["reading"]}
        
        # Get child payload
        child = grammar.crossover_payloads(payload1, payload2)
        
        assert isinstance(child, dict)
        # Child should have fields from both parents
        assert len(child) > 0
        
        # Make sure child has some fields from either parent
        parent_fields = set(payload1.keys()).union(set(payload2.keys()))
        child_fields = set(child.keys())
        assert len(child_fields.intersection(parent_fields)) > 0
    
    def test_mutate_payload(self):
        """Test payload mutation function."""
        original = {"name": "Original", "age": 30}
        
        # Mutate the payload
        mutated = grammar.mutate_payload(original)
        
        assert isinstance(mutated, dict)
        assert len(mutated) > 0
        
        # Check that something was actually mutated
        # Either a field was added, removed, or changed
        assert mutated != original
    
    def test_payload_serialization(self):
        """Test that all generated payloads are JSON serializable."""
        payloads = [
            grammar.generate_auth_payload(),
            grammar.generate_user_payload(),
            grammar.generate_random_payload()
        ]
        
        for payload in payloads:
            try:
                json_str = json.dumps(payload)
                # Deserialize to ensure it's valid
                decoded = json.loads(json_str)
                assert decoded == payload
            except (TypeError, json.JSONDecodeError) as e:
                pytest.fail(f"Payload {payload} is not properly JSON serializable: {str(e)}")

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])

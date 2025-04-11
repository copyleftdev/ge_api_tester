"""
Payload tracker module for storing and analyzing interesting API payloads.
Enhanced to support tracking various types of interesting responses from our realistic API.
"""
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayloadTracker:
    """
    Tracks and stores interesting payloads found during the test run,
    categorizing them by type of interest (server errors, validation issues, etc.)
    """
    
    def __init__(self, max_tracked_items=100, output_dir="./tracked_payloads"):
        """
        Initialize the payload tracker.
        
        Args:
            max_tracked_items: Maximum number of payloads to track per category
            output_dir: Directory to save tracked payloads to
        """
        self.output_dir = output_dir
        self.max_tracked_items = max_tracked_items
        
        # Create the output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize tracking categories
        self.high_fitness_payloads = []
        self.server_errors = []
        self.validation_errors = []
        self.slow_responses = []
        self.timeouts = []
        self.sql_injection_hits = []
        self.memory_issues = []
        self.auth_issues = []
        self.auth_tokens = []  # Store authentication tokens
        
        # Authentication token storage for testing authenticated endpoints
        self._auth_token = None
        
        # Ensure the output directory is properly saved to disk for Docker volumes
        if not os.path.isabs(output_dir):
            self.abs_output_dir = os.path.abspath(output_dir)
        else:
            self.abs_output_dir = output_dir
        
        logger.info(f"PayloadTracker initialized with output directory: {output_dir}")
    
    def _add_tracked_item(self, category: List[Dict[str, Any]], payload: Dict[str, Any], 
                          response_info: Dict[str, Any], extra_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an item to a tracking category, maintaining max size limit.
        
        Args:
            category: The category list to add to
            payload: The API payload
            response_info: Information about the API response
            extra_info: Any additional information to store
        """
        timestamp = datetime.now().isoformat()
        
        tracked_item = {
            "timestamp": timestamp,
            "payload": payload,
            "response": response_info,
        }
        
        # Add any extra information if provided
        if extra_info:
            tracked_item.update(extra_info)
        
        # Add to the category, ensuring we don't exceed the maximum
        category.append(tracked_item)
        if len(category) > self.max_tracked_items:
            category.pop(0)  # Remove oldest item
    
    def track_high_fitness(self, payload: Dict[str, Any], response_info: Dict[str, Any], 
                           fitness_score: float) -> None:
        """
        Track a payload that resulted in a high fitness score.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
            fitness_score: The calculated fitness score
        """
        self._add_tracked_item(
            self.high_fitness_payloads, 
            payload, 
            response_info,
            {"fitness_score": fitness_score}
        )
        logger.debug(f"Tracked high fitness payload with score: {fitness_score}")
    
    def track_server_error(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        """
        Track a payload that resulted in a server error (5xx).
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.server_errors, payload, response_info)
        logger.debug(f"Tracked server error with status: {response_info.get('status_code')}")
    
    def track_validation_error(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        """
        Track a payload that resulted in a validation error (4xx).
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.validation_errors, payload, response_info)
        logger.debug(f"Tracked validation error with status: {response_info.get('status_code')}")
    
    def track_slow_response(self, payload: Dict[str, Any], response_info: Dict[str, Any], 
                            response_time: float) -> None:
        """
        Track a payload that resulted in a slow response.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
            response_time: The response time in seconds
        """
        self._add_tracked_item(
            self.slow_responses, 
            payload, 
            response_info,
            {"response_time": response_time}
        )
        logger.debug(f"Tracked slow response: {response_time:.2f}s")
    
    def track_timeout(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        """
        Track a payload that resulted in a timeout.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.timeouts, payload, response_info)
        logger.debug("Tracked timeout")
    
    def track_sql_injection_hit(self, payload: Dict[str, Any], response_info: Dict[str, Any] = None) -> None:
        """
        Track a payload that may have triggered SQL injection detection.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.sql_injection_hits, payload, response_info or {})
        logger.debug("Tracked potential SQL injection pattern")
    
    def track_memory_issue(self, payload: Dict[str, Any], response_info: Dict[str, Any] = None) -> None:
        """
        Track a payload that may have triggered memory-related issues.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.memory_issues, payload, response_info or {})
        logger.debug("Tracked potential memory issue")
    
    def track_auth_issue(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        """
        Track a payload related to authentication errors or interesting auth patterns.
        
        Args:
            payload: The API payload
            response_info: Information about the API response
        """
        self._add_tracked_item(self.auth_issues, payload, response_info)
        logger.debug(f"Tracked auth issue with status: {response_info.get('status_code')}")
    
    def track_auth_token_update(self, token, auth_data):
        """
        Track an authentication token update
        
        Args:
            token: The new authentication token
            auth_data: Full authentication response data
        """
        self.auth_tokens.append({
            "token": token,
            "timestamp": time.time(),
            "expires_at": auth_data.get("expires_at"),
            "user_id": auth_data.get("user_id")
        })
        
        # Limit stored tokens to most recent ones
        if len(self.auth_tokens) > 10:
            self.auth_tokens = self.auth_tokens[-10:]
    
    def get_auth_token(self) -> Optional[str]:
        """
        Get the current authentication token for API requests.
        
        Returns:
            The current auth token or None if not set
        """
        return self._auth_token
    
    def set_auth_token(self, token: str) -> None:
        """
        Set the authentication token for future API requests.
        
        Args:
            token: The authentication token to use
        """
        self._auth_token = token
        logger.info("Authentication token updated")
    
    def save_to_disk(self) -> None:
        """
        Save all tracked payloads to JSON files.
        
        Returns:
            dict: Mapping of categories to saved file paths
        """
        timestamp = int(time.time())
        saved_files = {}
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Save high fitness payloads
        if self.high_fitness_payloads:
            file_path = os.path.join(self.output_dir, f"high_fitness_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.high_fitness_payloads, f, indent=2)
            saved_files['high_fitness'] = file_path
            logger.info(f"Saved {len(self.high_fitness_payloads)} high_fitness to {file_path}")
        
        # Save server errors
        if self.server_errors:
            file_path = os.path.join(self.output_dir, f"server_errors_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.server_errors, f, indent=2)
            saved_files['server_errors'] = file_path
            logger.info(f"Saved {len(self.server_errors)} server_errors to {file_path}")
        
        # Save validation errors
        if self.validation_errors:
            file_path = os.path.join(self.output_dir, f"validation_errors_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.validation_errors, f, indent=2)
            saved_files['validation_errors'] = file_path
            logger.info(f"Saved {len(self.validation_errors)} validation_errors to {file_path}")
        
        # Save slow responses
        if self.slow_responses:
            file_path = os.path.join(self.output_dir, f"slow_responses_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.slow_responses, f, indent=2)
            saved_files['slow_responses'] = file_path
            logger.info(f"Saved {len(self.slow_responses)} slow_responses to {file_path}")
        
        # Save timeouts
        if self.timeouts:
            file_path = os.path.join(self.output_dir, f"timeouts_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.timeouts, f, indent=2)
            saved_files['timeouts'] = file_path
            logger.info(f"Saved {len(self.timeouts)} timeouts to {file_path}")
        
        # Save SQL injection hits
        if self.sql_injection_hits:
            file_path = os.path.join(self.output_dir, f"sql_injection_hits_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.sql_injection_hits, f, indent=2)
            saved_files['sql_injection_hits'] = file_path
            logger.info(f"Saved {len(self.sql_injection_hits)} sql_injection_hits to {file_path}")
        
        # Save memory issues
        if self.memory_issues:
            file_path = os.path.join(self.output_dir, f"memory_issues_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.memory_issues, f, indent=2)
            saved_files['memory_issues'] = file_path
            logger.info(f"Saved {len(self.memory_issues)} memory_issues to {file_path}")
        
        # Save auth issues
        if self.auth_issues:
            file_path = os.path.join(self.output_dir, f"auth_issues_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.auth_issues, f, indent=2)
            saved_files['auth_issues'] = file_path
            logger.info(f"Saved {len(self.auth_issues)} auth_issues to {file_path}")
        
        # Create a manifest file to help the test discovery process
        manifest_path = os.path.join(self.output_dir, "payload_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "files": saved_files,
                "counts": {
                    "high_fitness": len(self.high_fitness_payloads),
                    "server_errors": len(self.server_errors),
                    "validation_errors": len(self.validation_errors),
                    "slow_responses": len(self.slow_responses),
                    "timeouts": len(self.timeouts),
                    "sql_injection_hits": len(self.sql_injection_hits),
                    "memory_issues": len(self.memory_issues),
                    "auth_issues": len(self.auth_issues)
                }
            }, f, indent=2)
        
        # Add debug info for file locations
        with open(os.path.join(self.output_dir, "debug_info.txt"), 'w') as f:
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Output directory: {self.output_dir}\n")
            f.write(f"Absolute path: {os.path.abspath(self.output_dir)}\n")
            f.write(f"Files in directory: {os.listdir(self.output_dir)}\n")
        
        return saved_files
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the tracked payloads.
        
        Returns:
            Dictionary with counts for each category
        """
        return {
            "high_fitness": len(self.high_fitness_payloads),
            "server_errors": len(self.server_errors),
            "validation_errors": len(self.validation_errors),
            "slow_responses": len(self.slow_responses),
            "timeouts": len(self.timeouts),
            "sql_injection_hits": len(self.sql_injection_hits),
            "memory_issues": len(self.memory_issues),
            "auth_issues": len(self.auth_issues)
        }
    
    def print_summary(self) -> None:
        """
        Print a summary of tracked payloads to the console.
        """
        stats = self.get_statistics()
        
        print("\n=== Payload Tracker Summary ===")
        print(f"Total tracked items: {sum(stats.values())}")
        for category, count in stats.items():
            print(f"  {category}: {count}")
        
        # Print some examples of high-value findings if available
        categories_to_show = [
            ("server_errors", self.server_errors),
            ("sql_injection_hits", self.sql_injection_hits),
            ("memory_issues", self.memory_issues)
        ]
        
        print("\n=== Example Findings ===")
        for category_name, items in categories_to_show:
            if items:
                print(f"\n--- {category_name} (showing 1 of {len(items)}) ---")
                example = items[-1]  # Show the most recent
                print(f"Payload: {json.dumps(example['payload'], indent=2)}")
                print(f"Response status: {example['response'].get('status_code')}")
                
                # Show error message if present
                response_data = example['response'].get('data', {})
                if isinstance(response_data, dict) and 'error' in response_data:
                    print(f"Error: {response_data['error']}")

# Create a singleton instance
payload_tracker = PayloadTracker()
